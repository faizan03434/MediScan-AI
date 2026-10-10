"""Research U-Net segmentation with fixed provider validation; no clinical/test claim."""
import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from train_medical_pilots import ROOT, checked_path


def block(inputs, outputs):
    return nn.Sequential(nn.Conv2d(inputs, outputs, 3, padding=1), nn.GroupNorm(2, outputs), nn.ReLU(),
        nn.Conv2d(outputs, outputs, 3, padding=1), nn.GroupNorm(2, outputs), nn.ReLU())


class WoundUNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder1, self.encoder2 = block(3, 8), block(8, 16)
        self.bridge = block(16, 32)
        self.decoder2, self.decoder1 = block(48, 16), block(24, 8)
        self.pool = nn.MaxPool2d(2)
        self.output = nn.Conv2d(8, 1, 1)

    def forward(self, images):
        first = self.encoder1(images)
        second = self.encoder2(self.pool(first))
        bridge = self.bridge(self.pool(second))
        up = nn.functional.interpolate(bridge, size=second.shape[-2:], mode='bilinear', align_corners=False)
        up = self.decoder2(torch.cat([up, second], dim=1))
        up = nn.functional.interpolate(up, size=first.shape[-2:], mode='bilinear', align_corners=False)
        return self.output(self.decoder1(torch.cat([up, first], dim=1)))


def binary_scores(prediction, truth):
    dims = (1, 2, 3)
    intersection = (prediction * truth).sum(dims)
    total = prediction.sum(dims) + truth.sum(dims)
    return ((2 * intersection + 1e-6) / (total + 1e-6),
            (intersection + 1e-6) / (total - intersection + 1e-6))


def run(epochs, patience, output):
    if epochs < 1 or patience < 1 or output.exists():
        raise ValueError('Positive epochs/patience and immutable new output required')
    torch.set_num_threads(4)
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)
    directory = ROOT / 'datasets/kaggle/co2wounds_v1'
    manifest_path = directory / 'cleaned/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('clinical_ready') is not False:
        raise ValueError('Explicit research-only manifest required')
    cache, pixels = {}, {}
    for split in ('train', 'val'):
        rows = [r for r in manifest['records'] if r.get('provider_splits') == [split] and r.get('mask_path')]
        images, masks = [], []
        for row in rows:
            image_path = checked_path(directory / 'raw', row['path'], row['sha256'])
            mask_path = checked_path(directory / 'raw', row['mask_path'], row['mask_sha256'])
            with Image.open(image_path) as image, Image.open(mask_path) as mask:
                values = np.asarray(mask)
                if image.size != mask.size or values.ndim != 2 or not set(np.unique(values)).issubset({0, 1}):
                    raise ValueError('Mask dimensions or class values invalid')
                image_tensor = torch.from_numpy(np.asarray(image.convert('RGB').resize((96, 96)),
                    dtype=np.float32).copy().transpose(2, 0, 1)) / 255
                mask_tensor = torch.from_numpy(np.asarray(mask.resize((96, 96), Image.Resampling.NEAREST),
                    dtype=np.float32).copy()).unsqueeze(0)
                if not mask_tensor.any():
                    raise ValueError('Wound vanished at training resolution; review resolution before training')
                images.append(image_tensor)
                masks.append(mask_tensor)
        if not images:
            raise ValueError('Missing annotated split')
        pixels[split] = {r['pixel_sha256'] for r in rows}
        cache[split] = torch.stack(images), torch.stack(masks)
    if pixels['train'] & pixels['val']:
        raise ValueError('Exact pixel split leakage')
    model = WoundUNet()
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0005, weight_decay=.001)
    loss_fn = nn.BCEWithLogitsLoss()
    loader = DataLoader(TensorDataset(*cache['train']), batch_size=16, shuffle=True)
    output.mkdir(parents=True)
    best, stale, history = -1, 0, []
    for epoch in range(epochs):
        model.train()
        for images, truth in loader:
            flip = torch.rand(len(images)) < .5
            images, truth = images.clone(), truth.clone()
            images[flip], truth[flip] = images[flip].flip(-1), truth[flip].flip(-1)
            optimizer.zero_grad()
            logits = model(images)
            probabilities = logits.sigmoid()
            soft_dice = (2 * (probabilities * truth).sum() + 1) / (probabilities.sum() + truth.sum() + 1)
            loss = loss_fn(logits, truth) + 1 - soft_dice
            loss.backward()
            optimizer.step()
        model.eval()
        dice, iou = [], []
        with torch.no_grad():
            for images, truth in DataLoader(TensorDataset(*cache['val']), batch_size=16):
                values = binary_scores((model(images).sigmoid() >= .5).float(), truth)
                dice.extend(values[0].tolist())
                iou.extend(values[1].tolist())
        score = float(np.mean(dice))
        history.append({'epoch': epoch + 1, 'validation_dice': score, 'validation_iou': float(np.mean(iou))})
        if score > best:
            best, stale, best_epoch, best_iou = score, 0, epoch + 1, float(np.mean(iou))
            torch.save(model.state_dict(), output / 'weights.pt')
        else:
            stale += 1
        (output / 'training_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
        print(f'U-Net epoch {epoch + 1}/{epochs}: validation Dice {score:.4f}', flush=True)
        if stale >= patience:
            break
    model.load_state_dict(torch.load(output / 'weights.pt', weights_only=True))
    model.eval()
    with torch.no_grad():
        logits = model(cache['val'][0][:1])
    assert logits.shape == (1, 1, 96, 96) and torch.isfinite(logits).all()
    card = {'model': output.name, 'architecture': 'WoundUNet', 'seed': 42,
        'epochs_completed': len(history), 'best_epoch': best_epoch, 'early_stopping_patience': patience,
        'validation_dice': best, 'validation_iou': best_iou, 'test_evaluated': False,
        'clinical_approved': False, 'commercial_release_allowed': False, 'patient_identity_verified': False,
        'split_identity': 'provider_split_patient_identity_unverified',
        'split_counts': {s: len(v[0]) for s, v in cache.items()},
        'checkpoint_sha256': hashlib.sha256((output / 'weights.pt').read_bytes()).hexdigest(),
        'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'threshold': .5, 'input_size': [96, 96], 'release_status': 'research_only_validation_selected',
        'preprocessing': 'RGB resize 96x96 /255; nearest-neighbour binary mask resize; matched horizontal flips in training',
        'checkpoint_load_forward_check_passed': True, 'healing_stage_supported': False,
        'calibrated_cm_supported': False, 'limitations': ['Provider test masks unavailable.',
            'Same validation cohort used for earlier experiments and checkpoint selection; score is optimistic.',
            'Patient IDs unverified; source license restrictions unresolved.',
            'Low-resolution research model, no clinical or commercial approval.']}
    (output / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    (ROOT.parent / 'docs/WOUND_UNET_RESULTS.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    print(json.dumps({'model': output.name, 'best_validation_dice': best, 'test_evaluated': False}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=60)
    parser.add_argument('--patience', type=int, default=12)
    parser.add_argument('--output', type=Path, default=ROOT / 'models/research/wound-unet-v1')
    args = parser.parse_args()
    run(args.epochs, args.patience, args.output)
