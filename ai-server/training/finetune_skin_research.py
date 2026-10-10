"""Fine-tune the last MobileNet block; select on validation, never load test pixels."""
import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import balanced_accuracy_score, classification_report, confusion_matrix
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from torchvision.models import mobilenet_v3_small

from train_skin_research import ROOT, validate_splits
from train_skin_transfer import TransferImages


def run(manifest_path, initial, output, epochs):
    if epochs < 1 or output.exists():
        raise ValueError('Positive epochs and a new immutable output directory required')
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(4)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    card = json.loads((initial / 'model_card.json').read_text(encoding='utf-8'))
    if manifest.get('clinical_ready') is not False or not manifest.get('patient_mapping_complete'):
        raise ValueError('Audited research patient manifest required')
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    weights = initial / 'weights.pt'
    if card['manifest_sha256'] != manifest_hash or card['checkpoint_sha256'] != hashlib.sha256(weights.read_bytes()).hexdigest():
        raise ValueError('Checkpoint/manifest integrity mismatch')
    splits = validate_splits(manifest['records'], 'patient_group')
    classes = sorted({r['label'] for r in manifest['records']})
    if classes != card['classes']:
        raise ValueError('Class order mismatch')
    model = mobilenet_v3_small(weights=None)
    model.classifier = nn.Sequential(nn.Dropout(.2), nn.Linear(576, len(classes)))
    model.load_state_dict(torch.load(weights, weights_only=True))
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    for module in (model.features[-1], model.classifier):
        for parameter in module.parameters():
            parameter.requires_grad_(True)
    # Cache only frozen prefix features. Training randomly flips these spatial maps.
    prefix = model.features[:-1].eval()
    cache = {}
    for split in ('train', 'val'):
        for row in splits[split]:
            path = (manifest_path.parent / row['path']).resolve()
            if not path.is_relative_to(manifest_path.parent.resolve()):
                raise ValueError('Image path escape')
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('Image integrity mismatch')
        loader = DataLoader(TransferImages(splits[split], manifest_path.parent, classes), batch_size=16)
        maps, labels = [], []
        with torch.no_grad():
            for images, truth in loader:
                maps.append(prefix(images))
                labels.append(truth)
        cache[split] = torch.cat(maps), torch.cat(labels)
        print(f'Cached frozen prefix: {split} {len(splits[split])}', flush=True)
    loader = DataLoader(TensorDataset(*cache['train']), batch_size=32, shuffle=True)
    counts = torch.bincount(cache['train'][1], minlength=len(classes)).float()
    loss_fn = nn.CrossEntropyLoss(weight=counts.sum() / (len(classes) * counts))
    optimizer = torch.optim.AdamW([
        {'params': model.features[-1].parameters(), 'lr': .0001},
        {'params': model.classifier.parameters(), 'lr': .0003}], weight_decay=.01)
    output.mkdir(parents=True)
    best, history = -1, []
    for epoch in range(epochs):
        model.eval()  # Keep pretrained batch-normalization statistics fixed.
        model.classifier.train()
        for batch, truth in loader:
            flip = torch.rand(len(batch)) < .5
            batch = batch.clone()
            batch[flip] = batch[flip].flip(-1)
            optimizer.zero_grad()
            logits = model.classifier(model.avgpool(model.features[-1](batch)).flatten(1))
            loss = loss_fn(logits, truth)
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            logits = model.classifier(model.avgpool(model.features[-1](cache['val'][0])).flatten(1))
            predicted = logits.argmax(1).tolist()
        truth = cache['val'][1].tolist()
        score = float(balanced_accuracy_score(truth, predicted))
        history.append({'epoch': epoch + 1, 'validation_balanced_accuracy': score})
        if score > best:
            best = score
            torch.save(model.state_dict(), output / 'weights.pt')
            result = {'best_epoch': epoch + 1, 'validation_balanced_accuracy': best,
                'validation_confusion_matrix': confusion_matrix(truth, predicted).tolist(),
                'validation_report': classification_report(truth, predicted, target_names=classes,
                    labels=list(range(len(classes))), output_dict=True, zero_division=0)}
        print(f'Epoch {epoch + 1}/{epochs}: validation balanced accuracy {score:.4f}', flush=True)
    card.update(result)
    card.update({'model': output.name, 'architecture': 'MobileNetV3SmallLastBlockFinetuned',
        'initial_checkpoint_sha256': card['checkpoint_sha256'],
        'checkpoint_sha256': hashlib.sha256((output / 'weights.pt').read_bytes()).hexdigest(),
        'epochs_completed': len(history), 'test_evaluated': False,
        'clinical_approved': False, 'commercial_release_allowed': False,
        'training_method': 'Frozen prefix, last block and head AdamW; spatial feature-map horizontal flip; fixed BN statistics',
        'limitations': card['limitations'] + ['Feature-map flipping is not equivalent to image augmentation',
            'Patient-group identifiers have not been independently clinically verified']})
    (output / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    (output / 'training_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), 'best_validation_balanced_accuracy': best, 'test_evaluated': False}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=ROOT / 'datasets/kaggle/skindisnet_3_v1/research_patient_manifest.json')
    parser.add_argument('--initial', type=Path, default=ROOT / 'models/research/skindisnet-mobilenet-v1')
    parser.add_argument('--output', type=Path, default=ROOT / 'models/research/skindisnet-finetuned-v1')
    parser.add_argument('--epochs', type=int, default=30)
    args = parser.parse_args()
    run(args.manifest, args.initial, args.output, args.epochs)
