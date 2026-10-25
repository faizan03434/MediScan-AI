"""Compare segmentation checkpoints on the same original-resolution validation masks."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from train_medical_pilots import ROOT, checked_path
from train_wound_unet_research import WoundUNet


def overlap(prediction, truth):
    intersection = np.count_nonzero(prediction & truth)
    total = np.count_nonzero(prediction) + np.count_nonzero(truth)
    return ((2 * intersection + 1e-6) / (total + 1e-6),
            (intersection + 1e-6) / (total - intersection + 1e-6))


def compare(checkpoints, output):
    if output.exists():
        raise ValueError('Comparison results are immutable; choose a new output file')
    torch.set_num_threads(2)
    directory = ROOT / 'datasets/kaggle/co2wounds_v1'
    manifest_path = directory / 'cleaned/manifest.json'
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('clinical_ready') is not False:
        raise ValueError('Explicit research manifest required')
    rows = [r for r in manifest['records'] if r.get('provider_splits') == ['val'] and r.get('mask_path')]
    if not rows:
        raise ValueError('No annotated validation cohort')
    models = []
    for checkpoint in checkpoints:
        card = json.loads((checkpoint / 'model_card.json').read_text(encoding='utf-8'))
        if card.get('architecture') != 'WoundUNet' or card.get('manifest_sha256') != digest:
            raise ValueError('Architecture or validation cohort mismatch')
        weights = checkpoint / 'weights.pt'
        if hashlib.sha256(weights.read_bytes()).hexdigest() != card['checkpoint_sha256']:
            raise ValueError('Checkpoint integrity mismatch')
        model = WoundUNet()
        model.load_state_dict(torch.load(weights, weights_only=True, map_location='cpu'))
        model.eval()
        models.append((card, model))
    scores = {card['model']: [] for card, _ in models}
    for index, row in enumerate(rows):
        path = checked_path(directory / 'raw', row['path'], row['sha256'])
        mask_path = checked_path(directory / 'raw', row['mask_path'], row['mask_sha256'])
        with Image.open(path) as image, Image.open(mask_path) as mask:
            if image.size != mask.size or image.width * image.height > 25_000_000:
                raise ValueError('Invalid original mask geometry or pixel budget')
            truth = np.asarray(mask)
            if truth.ndim != 2 or not set(np.unique(truth)).issubset({0, 1}):
                raise ValueError('Expected a binary original-resolution mask')
            truth = truth.astype(bool)
            for card, model in models:
                size = card['input_size']
                tensor = torch.from_numpy(np.asarray(image.convert('RGB').resize(tuple(size)),
                    dtype=np.float32).transpose(2, 0, 1).copy()).unsqueeze(0) / 255
                with torch.inference_mode():
                    logits = model(tensor)
                    logits = torch.nn.functional.interpolate(logits, size=truth.shape,
                        mode='bilinear', align_corners=False)
                    prediction = (logits.sigmoid() >= card['threshold'])[0, 0].numpy()
                scores[card['model']].append(overlap(prediction, truth))
        if (index + 1) % 20 == 0:
            print(f'Native-mask comparison {index + 1}/{len(rows)}', flush=True)
    result = {'evaluation': 'same_original_resolution_validation_masks', 'validation_images': len(rows),
        'manifest_sha256': digest, 'test_evaluated': False, 'clinical_approved': False,
        'models': {name: {'validation_dice': float(np.mean(values, axis=0)[0]),
            'validation_iou': float(np.mean(values, axis=0)[1])} for name, values in scores.items()},
        'limitations': ['Reused checkpoint-selection validation; no independent performance estimate.',
            'Provider subject identities unverified; no clinical acceptance or calibrated measurement claim.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoints', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    compare(args.checkpoints, args.output)
