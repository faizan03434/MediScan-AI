"""Exploratory cleaned-data baselines. No patient independence or clinical approval claimed."""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from sklearn.metrics import balanced_accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

ROOT = Path(__file__).resolve().parents[1]


def checked_path(root, relative, digest):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not digest:
        raise ValueError('Missing integrity field or unsafe path')
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Source changed after audit')
    return path


def exploratory_split(rows):
    """Explicit image-level split; never pretend missing patient IDs were supplied."""
    if len({r['pixel_sha256'] for r in rows}) != len(rows):
        raise ValueError('Exact pixel duplicates must be resolved before splitting')
    ids = list(range(len(rows)))
    train, rest = train_test_split(ids, test_size=.3, stratify=[r['label'] for r in rows], random_state=42)
    val, test = train_test_split(rest, test_size=.5, stratify=[rows[i]['label'] for i in rest], random_state=42)
    return {'train': train, 'val': val, 'test': test}


def save_card(output, card):
    card.update({'clinical_approved': False, 'commercial_release_allowed': False,
        'patient_identity_verified': False, 'release_status': 'exploratory_research_only',
        'checkpoint_sha256': hashlib.sha256((output / 'weights.pt').read_bytes()).hexdigest(),
        'limitations': ['Patient identifiers are unavailable/unverified; no patient-independent performance claim.',
            'Source annotation and original permission review remain unresolved.',
            'Internal image-level performance is not clinical accuracy or a deployment approval.']})
    (output / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    from report_medical_training import report
    report()
    print(json.dumps({'model': output.name, 'result': card.get('test_balanced_accuracy', card.get('validation_dice')),
                      'clinical_approved': False}), flush=True)


def classification(name, directory, manifest_file, epochs):
    output = ROOT / 'models/research' / (name + '-pilot-v1')
    if output.exists():
        raise ValueError('Immutable run exists; choose a new run name')
    manifest = json.loads((directory / manifest_file).read_text(encoding='utf-8'))
    if manifest.get('clinical_ready') is not False:
        raise ValueError('Explicit research-only manifest required')
    rows = manifest['records']
    splits = exploratory_split(rows)
    classes = sorted({r['label'] for r in rows})
    pretrained = ROOT / 'models/pretrained/mobilenet_v3_small-047dcff4.pth'
    if not hashlib.sha256(pretrained.read_bytes()).hexdigest().startswith('047dcff4'):
        raise ValueError('Pretrained checkpoint integrity mismatch')
    backbone = mobilenet_v3_small(weights=None)
    backbone.load_state_dict(torch.load(pretrained, weights_only=True))
    backbone.classifier = nn.Identity()
    backbone.eval()
    transform = MobileNet_V3_Small_Weights.DEFAULT.transforms()
    cache = {}
    # Only train/val features extracted during checkpoint selection.
    def features(indices):
        batches, labels = [], []
        for start in range(0, len(indices), 16):
            batch = []
            for i in indices[start:start + 16]:
                row = rows[i]
                path = checked_path(directory / 'raw', row['path'], row['sha256'])
                with Image.open(path) as image:
                    batch.append(transform(ImageOps.exif_transpose(image).convert('RGB')))
                labels.append(classes.index(row['label']))
            with torch.no_grad():
                batches.append(backbone(torch.stack(batch)))
        return torch.cat(batches), torch.tensor(labels)
    for split in ('train', 'val'):
        cache[split] = features(splits[split])
        print(f'{name}: extracted {split} ({len(splits[split])})', flush=True)
    head = nn.Sequential(nn.Dropout(.2), nn.Linear(576, len(classes)))
    counts = torch.bincount(cache['train'][1], minlength=len(classes)).float()
    criterion = nn.CrossEntropyLoss(weight=counts.sum() / (len(classes) * counts))
    optimizer = torch.optim.AdamW(head.parameters(), lr=.001, weight_decay=.01)
    loader = DataLoader(TensorDataset(*cache['train']), batch_size=32, shuffle=True)
    output.mkdir(parents=True)
    best, history = -1, []
    for epoch in range(epochs):
        head.train()
        for images, truth in loader:
            optimizer.zero_grad()
            loss = criterion(head(images), truth)
            loss.backward()
            optimizer.step()
        head.eval()
        with torch.no_grad():
            pred = head(cache['val'][0]).argmax(1).tolist()
        score = float(balanced_accuracy_score(cache['val'][1].tolist(), pred))
        history.append({'epoch': epoch + 1, 'validation_balanced_accuracy': score})
        if score > best:
            best, best_epoch = score, epoch + 1
            backbone.classifier = head
            torch.save(backbone.state_dict(), output / 'weights.pt')
            backbone.classifier = nn.Identity()
    backbone.classifier = head
    backbone.load_state_dict(torch.load(output / 'weights.pt', weights_only=True))
    backbone.classifier = nn.Identity()
    head.eval()
    test_features, truth = features(splits['test'])
    with torch.no_grad():
        probabilities = head(test_features).softmax(1).numpy()
    predicted = probabilities.argmax(1)
    split_manifest = {'split_identity': 'image_level_not_patient', 'source_manifest_sha256':
        hashlib.sha256((directory / manifest_file).read_bytes()).hexdigest(),
        'records': [{**rows[i], 'split': s} for s, indices in splits.items() for i in indices]}
    (output / 'experiment_manifest.json').write_text(json.dumps(split_manifest, indent=2), encoding='utf-8')
    (output / 'training_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
    save_card(output, {'model': output.name, 'architecture': 'MobileNetV3SmallFrozen', 'classes': classes,
        'epochs_completed': epochs, 'seed': 42, 'best_epoch': best_epoch,
        'split_counts': {s: len(v) for s, v in splits.items()}, 'split_identity': 'image_level_not_patient',
        'label_semantics': 'Unverified source labels; not clinically confirmed diagnoses',
        'validation_balanced_accuracy': best, 'test_evaluated': True,
        'test_balanced_accuracy': float(balanced_accuracy_score(truth.numpy(), predicted)),
        'test_roc_auc': float(roc_auc_score(truth.numpy(), probabilities[:, 1])) if len(classes) == 2 else None,
        'test_confusion_matrix': confusion_matrix(truth.numpy(), predicted).tolist(),
        'test_report': classification_report(truth.numpy(), predicted, labels=list(range(len(classes))),
            target_names=classes, output_dict=True, zero_division=0)})


class WoundSegmenter(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.Conv2d(32, 16, 3, padding=1),
            nn.ReLU(), nn.Conv2d(16, 1, 1))

    def forward(self, images):
        return self.layers(images)


def segmentation(epochs):
    directory = ROOT / 'datasets/kaggle/co2wounds_v1'
    output = ROOT / 'models/research/wound-segmentation-pilot-v1'
    if output.exists():
        raise ValueError('Immutable output exists')
    manifest = json.loads((directory / 'cleaned/manifest.json').read_text())
    if manifest.get('clinical_ready') is not False:
        raise ValueError('Research-only manifest required')
    cache = {}
    used = []
    for split in ('train', 'val'):
        rows = [r for r in manifest['records'] if r.get('provider_splits') == [split] and r.get('mask_path')]
        images, masks = [], []
        for row in rows:
            image_path = checked_path(directory / 'raw', row['path'], row['sha256'])
            mask_path = checked_path(directory / 'raw', row['mask_path'], row['mask_sha256'])
            with Image.open(image_path) as image, Image.open(mask_path) as mask:
                if image.size != mask.size or not set(np.unique(np.array(mask))).issubset({0, 1}):
                    raise ValueError('Invalid binary mask or dimensions')
                images.append(torch.from_numpy(np.asarray(image.convert('RGB').resize((96, 96)),
                    dtype=np.float32).copy().transpose(2, 0, 1)) / 255)
                masks.append(torch.from_numpy(np.asarray(mask.resize((96, 96), Image.Resampling.NEAREST),
                    dtype=np.float32).copy()).unsqueeze(0))
            used.append({**row, 'split': split})
        if not rows:
            raise ValueError('No annotated data for split')
        cache[split] = torch.stack(images), torch.stack(masks)
    if {r['pixel_sha256'] for r in used if r['split'] == 'train'} & {r['pixel_sha256'] for r in used if r['split'] == 'val'}:
        raise ValueError('Pixel split leakage')
    model = WoundSegmenter()
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
    criterion = nn.BCEWithLogitsLoss()
    loader = DataLoader(TensorDataset(*cache['train']), batch_size=16, shuffle=True)
    output.mkdir(parents=True)
    best, history = -1, []
    for epoch in range(epochs):
        model.train()
        for images, masks in loader:
            optimizer.zero_grad()
            logits = model(images)
            probabilities = logits.sigmoid()
            soft_dice = (2 * (probabilities * masks).sum() + 1) / (probabilities.sum() + masks.sum() + 1)
            loss = criterion(logits, masks) + 1 - soft_dice
            loss.backward()
            optimizer.step()
        model.eval()
        dice, iou = [], []
        with torch.no_grad():
            for images, masks in DataLoader(TensorDataset(*cache['val']), batch_size=16):
                pred = (model(images).sigmoid() >= .5).float()
                dims = (1, 2, 3)
                intersection = (pred * masks).sum(dims)
                total = pred.sum(dims) + masks.sum(dims)
                dice.extend(((2 * intersection + 1e-6) / (total + 1e-6)).tolist())
                iou.extend(((intersection + 1e-6) / (total - intersection + 1e-6)).tolist())
        score = float(np.mean(dice))
        history.append({'epoch': epoch + 1, 'validation_dice': score, 'validation_iou': float(np.mean(iou))})
        if score > best:
            best, best_epoch, best_iou = score, epoch + 1, float(np.mean(iou))
            torch.save(model.state_dict(), output / 'weights.pt')
        print(f'wound: epoch {epoch + 1}/{epochs}, validation Dice {score:.4f}', flush=True)
    (output / 'training_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
    save_card(output, {'model': output.name, 'architecture': 'WoundSegmenter', 'epochs_completed': epochs,
        'best_epoch': best_epoch, 'validation_dice': best, 'validation_iou': best_iou,
        'split_counts': {s: len(v[0]) for s, v in cache.items()}, 'test_evaluated': False,
        'split_identity': 'provider_split_patient_identity_unverified', 'threshold': .5,
        'input_size': [96, 96], 'preprocessing': 'RGB resize 96x96 /255; masks nearest-neighbour',
        'test_limitation': 'Provider test masks unavailable; validation used for selection',
        'healing_stage_supported': False, 'calibrated_cm_supported': False})


def retina_pipeline(epochs, serial=False):
    """Resume public intake, remove duplicate candidates, then train a fundus-only pilot."""
    sys.path.insert(0, str(ROOT))
    from acquire_medical_research import acquire
    from training.clean_medical_intake import select_clean
    directory = ROOT / 'datasets/kaggle/retina_eye_classification_v1'
    if not (directory / 'audit/audit.json').exists():
        acquire('retina_eye_classification', serial=serial)
    rows = [json.loads(line) for line in (directory / 'audit/image_index.jsonl').read_text().splitlines() if line]
    near = json.loads((directory / 'audit/near_duplicates.json').read_text())
    accepted, quarantine, redundant = select_clean(rows, {}, near)
    manifest = {'clinical_ready': False, 'training_ready': False, 'patient_identity_verified': False,
        'labels_are_unverified_folder_names': True, 'records': accepted,
        'quarantine': quarantine, 'redundant': redundant}
    (directory / 'research_candidate_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    classification('retina-fundus', directory, 'research_candidate_manifest.json', epochs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--serial-intake', action='store_true', help='Use a continuous resumable stream instead of separate range chunks')
    parser.add_argument('--module', choices=['anemia', 'eye', 'wound', 'retina', 'available'], default='available')
    args = parser.parse_args()
    if args.epochs < 1:
        raise ValueError('Positive epochs required')
    torch.set_num_threads(4)
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    if args.module in ('anemia', 'available'):
        classification('anemia-conjunctiva', ROOT / 'datasets/kaggle/cp_anemic_v1', 'cleaned/manifest.json', args.epochs)
    if args.module in ('eye', 'available'):
        classification('eye-conjunctivitis', ROOT / 'datasets/kaggle/eye_conjunctivitis_alisofiya_v1',
                       'research_candidate_manifest.json', args.epochs)
    if args.module in ('wound', 'available'):
        segmentation(args.epochs)
    if args.module == 'retina':
        retina_pipeline(args.epochs, args.serial_intake)
