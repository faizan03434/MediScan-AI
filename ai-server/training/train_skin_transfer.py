"""Frozen ImageNet features with validation-only model selection; never reads test images."""
import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from sklearn.metrics import balanced_accuracy_score, classification_report, confusion_matrix
from torch import nn
from torch.utils.data import DataLoader, Dataset, TensorDataset
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

from train_skin_research import ROOT, validate_splits


class TransferImages(Dataset):
    def __init__(self, rows, root, classes):
        self.rows, self.root, self.classes = rows, root, classes
        self.transform = MobileNet_V3_Small_Weights.DEFAULT.transforms()

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(self.root / row['path']) as image:
            tensor = self.transform(ImageOps.exif_transpose(image).convert('RGB'))
        return tensor, self.classes.index(row['label'])


def extract_features(backbone, loader):
    features, labels = [], []
    backbone.eval()
    with torch.no_grad():
        for batch, truth in loader:
            features.append(backbone(batch))
            labels.append(truth)
    return torch.cat(features), torch.cat(labels)


def train(manifest_path, pretrained_path, output, epochs=100):
    if epochs < 1 or output.exists():
        raise ValueError('Use positive epochs and a new immutable output directory')
    torch.set_num_threads(4)
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('clinical_ready') is not False or not manifest.get('patient_mapping_complete'):
        raise ValueError('This experiment requires an audited research patient manifest')
    splits = validate_splits(manifest['records'], 'patient_group')
    classes = sorted({row['label'] for row in manifest['records']})
    # Test identity metadata is checked for leakage, but test image bytes are never loaded.
    for split in ('train', 'val'):
        for row in splits[split]:
            path = (manifest_path.parent / row['path']).resolve()
            if not path.is_relative_to(manifest_path.parent.resolve()):
                raise ValueError('Dataset path escape')
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('Image integrity mismatch')
    digest = hashlib.sha256(pretrained_path.read_bytes()).hexdigest()
    if not digest.startswith('047dcff4'):
        raise ValueError('Official pretrained checkpoint hash prefix mismatch')
    backbone = mobilenet_v3_small(weights=None)
    backbone.load_state_dict(torch.load(pretrained_path, weights_only=True))
    backbone.classifier = nn.Identity()
    for parameter in backbone.parameters():
        parameter.requires_grad_(False)
    features = {}
    for split in ('train', 'val'):
        print(f'Extracting frozen features: {split} ({len(splits[split])} images)', flush=True)
        loader = DataLoader(TransferImages(splits[split], manifest_path.parent, classes), batch_size=16)
        features[split] = extract_features(backbone, loader)
    head = nn.Sequential(nn.Dropout(.2), nn.Linear(576, len(classes)))
    counts = torch.bincount(features['train'][1], minlength=len(classes)).float()
    loss_fn = nn.CrossEntropyLoss(weight=counts.sum() / (len(classes) * counts))
    optimizer = torch.optim.AdamW(head.parameters(), lr=.001, weight_decay=.01)
    loader = DataLoader(TensorDataset(*features['train']), batch_size=32, shuffle=True)
    output.mkdir(parents=True)
    checkpoint = output / 'weights.pt'
    history, best, best_epoch, stale = [], -1, 0, 0
    for epoch in range(epochs):
        head.train()
        for batch, truth in loader:
            optimizer.zero_grad()
            loss = loss_fn(head(batch), truth)
            loss.backward()
            optimizer.step()
        head.eval()
        with torch.no_grad():
            pred = head(features['val'][0]).argmax(1).tolist()
        score = balanced_accuracy_score(features['val'][1].tolist(), pred)
        history.append({'epoch': epoch + 1, 'validation_balanced_accuracy': score})
        if score > best:
            best, best_epoch, stale = score, epoch + 1, 0
            backbone.classifier = head
            torch.save(backbone.state_dict(), checkpoint)
            backbone.classifier = nn.Identity()
        else:
            stale += 1
        print(f'Epoch {epoch + 1}: validation balanced accuracy {score:.3f}', flush=True)
        if stale >= 15:
            break
    final = mobilenet_v3_small(weights=None)
    final.classifier = head
    final.load_state_dict(torch.load(checkpoint, weights_only=True))
    head.eval()
    with torch.no_grad():
        pred = head(features['val'][0]).argmax(1).tolist()
    truth = features['val'][1].tolist()
    card = {'model': output.name, 'architecture': 'MobileNetV3SmallFrozen', 'classes': classes,
            'release_status': 'research_only_validation_selected', 'clinical_approved': False,
            'commercial_release_allowed': False, 'source_license': manifest.get('source_license'),
            'seed': 42, 'epochs_completed': len(history), 'best_epoch': best_epoch,
            'split_identity': 'patient_group', 'split_counts': {s: len(r) for s, r in splits.items()},
            'test_evaluated': False, 'validation_balanced_accuracy': best,
            'validation_confusion_matrix': confusion_matrix(truth, pred, labels=list(range(len(classes)))).tolist(),
            'validation_report': classification_report(truth, pred, labels=list(range(len(classes))),
                target_names=classes, output_dict=True, zero_division=0),
            'preprocessing': 'EXIF RGB, bilinear resize short edge 256, center crop 224, ImageNet mean/std',
            'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'pretrained_sha256': digest, 'pretrained_source': MobileNet_V3_Small_Weights.DEFAULT.url,
            'limitations': manifest['limitations'] + ['Validation used for checkpoint selection; score is optimistic',
                'Previously examined internal test is not a fresh external test',
                'No healthy/unknown-condition class, calibration or clinical approval']}
    (output / 'training_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
    (output / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    print(json.dumps(card, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=ROOT / 'datasets/kaggle/skindisnet_3_v1/research_patient_manifest.json')
    parser.add_argument('--pretrained', type=Path, default=ROOT / 'models/pretrained/mobilenet_v3_small-047dcff4.pth')
    parser.add_argument('--output', type=Path, default=ROOT / 'models/research/skindisnet-mobilenet-v1')
    parser.add_argument('--epochs', type=int, default=100)
    args = parser.parse_args()
    train(args.manifest, args.pretrained, args.output, args.epochs)
