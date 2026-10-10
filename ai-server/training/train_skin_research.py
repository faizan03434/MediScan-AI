"""Reproducible pilot CNN; checkpoints are not approved for patient inference."""
import argparse
import hashlib
import json
import random
from pathlib import Path
import numpy as np
import torch
from PIL import Image, ImageOps
from torch import nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import confusion_matrix, balanced_accuracy_score, classification_report

ROOT = Path(__file__).resolve().parents[1]

class SkinCNN(nn.Module):
    def __init__(self, classes=3):
        super().__init__()
        self.layers = nn.Sequential(nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1),
            nn.Flatten(), nn.Linear(64, classes))
    def forward(self, x):
        return self.layers(x)

def image_tensor(path):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert('RGB').resize((128, 128))
        return torch.from_numpy(np.array(image, dtype=np.float32).transpose(2, 0, 1).copy()) / 255

class Images(Dataset):
    def __init__(self, rows, directory, classes, cache=False):
        self.rows, self.directory, self.classes = rows, directory, classes
        self.cache = [image_tensor(directory / row['path']) for row in rows] if cache else None
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, i):
        row = self.rows[i]
        image = self.cache[i] if self.cache is not None else image_tensor(self.directory / row['path'])
        return image, self.classes.index(row['label'])


def validate_splits(rows, identity):
    if any(row.get('split') not in {'train', 'val', 'test'} for row in rows):
        raise ValueError('Every image must have an explicit train/val/test assignment')
    splits = {s: [r for r in rows if r['split'] == s] for s in ['train', 'val', 'test']}
    classes = {row['label'] for row in rows}
    if not classes or any({row['label'] for row in split} != classes for split in splits.values()):
        raise ValueError('Each split must contain every class')
    fields = [identity, 'sha256'] + (['pixel_sha256'] if all('pixel_sha256' in r for r in rows) else [])
    for field in fields:
        if any(not row.get(field) for row in rows):
            raise ValueError('Missing split identity or integrity field')
        groups = [set(r[field] for r in split) for split in splits.values()]
        if any(groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3)):
            raise ValueError('Split leakage')
    return splits

def evaluate(model, loader):
    model.eval()
    truth, predicted = [], []
    with torch.no_grad():
        for images, labels in loader:
            predicted.extend(model(images).argmax(1).tolist())
            truth.extend(labels.tolist())
    return truth, predicted

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=ROOT / 'datasets/scin/research_manifest.json')
    parser.add_argument('--epochs', type=int, default=20)
    parser.add_argument('--output', type=Path, default=ROOT / 'models/research/skin-cnn-v1')
    parser.add_argument('--cache-images', action='store_true', help='Cache resized tensors in RAM for faster CPU research runs')
    args = parser.parse_args()
    torch.set_num_threads(4)
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    if args.epochs < 1:
        raise ValueError('Epoch count must be positive')
    if (args.output / 'weights.pt').exists():
        raise ValueError('Choose a new output directory; existing research runs are immutable')
    rows = manifest['records']
    classes = manifest.get('classes') or sorted({r['label'] for r in rows})
    if manifest.get('clinical_ready') is not False:
        raise ValueError('This pipeline accepts explicitly marked research manifests only')
    identity = 'patient_group' if manifest.get('patient_mapping_complete') else 'case_id'
    splits = validate_splits(rows, identity)
    for row in rows:
        source = (args.manifest.parent / row['path']).resolve()
        if not source.is_relative_to(args.manifest.parent.resolve()):
            raise ValueError('Image path escapes dataset directory')
        if hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Image integrity mismatch')
    print('Verified splits and hashes; preparing image tensors', flush=True)
    loaders = {s: DataLoader(Images(v, args.manifest.parent, classes, args.cache_images), batch_size=8, shuffle=s == 'train') for s, v in splits.items()}
    model = SkinCNN(len(classes))
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    counts = torch.tensor([sum(r['label'] == c for r in splits['train']) for c in classes], dtype=torch.float32)
    loss_fn = nn.CrossEntropyLoss(weight=counts.sum() / (len(classes) * counts))
    directory = args.output
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint = directory / 'weights.pt'
    best = -1
    for epoch in range(args.epochs):
        model.train()
        for images, labels in loaders['train']:
            optimizer.zero_grad()
            loss = loss_fn(model(images), labels)
            loss.backward()
            optimizer.step()
        truth, pred = evaluate(model, loaders['val'])
        score = balanced_accuracy_score(truth, pred)
        if score > best:
            best = score
            torch.save(model.state_dict(), checkpoint)
        print(f'Epoch {epoch + 1}: validation balanced accuracy {score:.3f}', flush=True)
    model.load_state_dict(torch.load(checkpoint, weights_only=True))
    truth, pred = evaluate(model, loaders['test'])
    card = {'model': directory.name, 'architecture': 'SkinCNN', 'classes': classes,
        'epochs': args.epochs, 'seed': 42, 'split_identity': identity,
        'commercial_release_allowed': manifest.get('commercial_release_allowed', False),
        'source_license': manifest.get('source_license', 'See source dataset license'),
        'clinical_approved': False, 'release_status': 'research_only', 'preprocessing': 'EXIF transpose, RGB resize 128x128, float /255',
        'split_counts': {s: len(v) for s, v in splits.items()}, 'validation_balanced_accuracy': best,
        'test_balanced_accuracy': balanced_accuracy_score(truth, pred),
        'test_confusion_matrix': confusion_matrix(truth, pred, labels=list(range(len(classes)))).tolist(),
        'test_report': classification_report(truth, pred, labels=list(range(len(classes))), target_names=classes, output_dict=True, zero_division=0),
        'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        'manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        'limitations': manifest['limitations'] + ['Internal source-cohort testing cannot establish external clinical validity', 'No healthy class or out-of-distribution validation', 'Not approved for live patient inference']}
    (directory / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    print(json.dumps(card, indent=2))

if __name__ == '__main__':
    main()
