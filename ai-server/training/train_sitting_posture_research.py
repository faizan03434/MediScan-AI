"""Real provider-labelled sitting poses; subject-disjoint research, no synthetic data."""
import argparse
import csv
import hashlib
import json

import numpy as np
import torch
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path

from prepare_sitting_posture import DIRECTORY, LOWER, ROOT, UPPER, main as prepare


class SittingPostureTwoHead(nn.Module):
    def __init__(self):
        super().__init__()
        self.shared = nn.Sequential(nn.Linear(99, 64), nn.ReLU(), nn.Dropout(.2), nn.Linear(64, 32), nn.ReLU())
        self.upper = nn.Linear(32, 5)
        self.lower = nn.Linear(32, 7)

    def forward(self, values):
        features = self.shared(values)
        return self.upper(features), self.lower(features)


def normalize_pose(values):
    joints = values.reshape(-1, 33, 3)
    center = joints[:, [23, 24]].mean(1, keepdim=True)
    shoulder = joints[:, [11, 12]].mean(1, keepdim=True)
    scale = (shoulder - center).square().sum(-1, keepdim=True).sqrt()
    if not torch.isfinite(joints).all() or (scale < 1e-6).any():
        raise ValueError('Nonfinite or degenerate pose geometry')
    return ((joints - center) / scale).reshape(-1, 99)


def main(epochs=50, output=None, pose_normalization=False, skip_test=False):
    output = output or ROOT / 'models/research/sitting-posture-pilot-v1'
    if output.exists() or epochs < 1:
        raise ValueError('Immutable run exists')
    manifest_path = DIRECTORY / 'subject_manifest.json'
    if not manifest_path.exists():
        prepare()
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('clinical_ready') is not False or hashlib.sha256((DIRECTORY / 'data.csv').read_bytes()).hexdigest() != manifest['source_sha256']:
        raise ValueError('Research manifest or source integrity check failed')
    if pose_normalization:
        expected = {11: 'left_shoulder', 12: 'right_shoulder', 23: 'left_hip', 24: 'right_hip'}
        if any(manifest['features'][3 * joint:3 * joint + 3] != [name + suffix for suffix in ('_x', '_y', '_z')]
               for joint, name in expected.items()):
            raise ValueError('Pose schema does not match the landmark normalization contract')
    groups = [set(manifest['subject_splits'][s]) for s in ('train', 'val', 'test')]
    if any(groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3)):
        raise ValueError('Provider-subject split leakage')
    upper, lower = sorted(UPPER), sorted(LOWER)
    with (DIRECTORY / 'data.csv').open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    splits = {}
    for split, subjects in manifest['subject_splits'].items():
        if skip_test and split == 'test':
            continue
        selected = [r for r in rows if r['subject'] in subjects]
        x = torch.tensor([[float(r[c]) for c in manifest['features']] for r in selected], dtype=torch.float32)
        if pose_normalization:
            x = normalize_pose(x)
        y = torch.tensor([[upper.index(r['upperbody_label']), lower.index(r['lowerbody_label'])] for r in selected])
        if set(y[:, 0].tolist()) != set(range(5)) or set(y[:, 1].tolist()) != set(range(7)):
            raise ValueError('Split lacks classes; revise protocol without inspecting test performance')
        splits[split] = x, y
    torch.manual_seed(42)
    torch.set_num_threads(2)
    mean = splits['train'][0].mean(0)
    scale = splits['train'][0].std(0).clamp(min=1e-6)
    splits = {s: ((x - mean) / scale, y) for s, (x, y) in splits.items()}
    model = SittingPostureTwoHead()
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.01)
    losses = [nn.CrossEntropyLoss(weight=len(splits['train'][1]) / (count * torch.bincount(splits['train'][1][:, i], minlength=count)))
              for i, count in enumerate([5, 7])]
    loader = DataLoader(TensorDataset(*splits['train']), batch_size=64, shuffle=True)
    output.mkdir(parents=True)
    experiment = {'status': 'running', 'epochs_requested': epochs, 'test_evaluated': not skip_test,
        'pose_normalization': pose_normalization, 'clinical_approved': False}
    (output / 'experiment.json').write_text(json.dumps(experiment, indent=2), encoding='utf-8')
    history, best = [], -1
    for epoch in range(epochs):
        model.train()
        for x, y in loader:
            optimizer.zero_grad()
            predicted = model(x)
            loss = sum(losses[i](predicted[i], y[:, i]) for i in range(2))
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            predictions = model(splits['val'][0])
        scores = [balanced_accuracy_score(splits['val'][1][:, i], predictions[i].argmax(1)) for i in range(2)]
        score = float(np.mean(scores))
        history.append({'epoch': epoch + 1, 'validation_upper_balanced_accuracy': scores[0],
                        'validation_lower_balanced_accuracy': scores[1]})
        if score > best:
            best, best_epoch = score, epoch + 1
            torch.save({'state_dict': model.state_dict(), 'mean': mean, 'scale': scale}, output / 'weights.pt')
        if (epoch + 1) % 10 == 0:
            print(f'Sitting posture epoch {epoch + 1}: validation task-average {score:.4f}', flush=True)
    checkpoint = torch.load(output / 'weights.pt', weights_only=True)
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()
    evaluated_split = 'val' if skip_test else 'test'
    with torch.no_grad():
        predictions = model(splits[evaluated_split][0])
    if not all(torch.isfinite(p).all() for p in predictions):
        raise ValueError('Non-finite test output')
    tasks = {}
    for i, (name, classes) in enumerate([('upper_body', upper), ('lower_body', lower)]):
        truth, predicted = splits[evaluated_split][1][:, i], predictions[i].argmax(1)
        prefix = 'validation' if skip_test else 'test'
        tasks[name] = {'classes': classes, prefix + '_balanced_accuracy': float(balanced_accuracy_score(truth, predicted)),
                      prefix + '_confusion_matrix': confusion_matrix(truth, predicted, labels=range(len(classes))).tolist()}
    card = {'model': output.name, 'architecture': 'SittingPostureTwoHead', 'scope': 'sitting posture recognition only',
        'epochs_completed': epochs, 'best_epoch': best_epoch, 'seed': 42, 'tasks': tasks,
        'classes': upper, 'primary_task': 'upper_body',
        'split_counts': {s: len(x) for s, (x, _) in splits.items()},
        'subject_counts': {s: len(subjects) for s, subjects in manifest['subject_splits'].items()},
        'split_identity': 'provider_subject_disjoint_unverified_clinical_identity',
        'source_license': 'CC BY 4.0', 'features': manifest['features'], 'test_evaluated': not skip_test,
        'pose_normalization': 'hip-centered torso-length scaling' if pose_normalization else 'none',
        'external_test': False, 'patient_identity_verified': False, 'clinical_ground_truth_reviewed': False,
        'clinical_approved': False, 'commercial_release_allowed': False, 'scoliosis_supported': False,
        'checkpoint_sha256': hashlib.sha256((output / 'weights.pt').read_bytes()).hexdigest(),
        'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'limitations': ['Only 13 provider subjects; repeated frames are correlated, not independent test patients.',
            'Provider labels describe sitting positions, not scoliosis, pain, or clinical severity.',
            'No raw camera pipeline or independent site/device evaluation; no diagnostic approval.',
            'Validation selection is optimistic; repeated frames are not independent patients.']}
    if not skip_test:
        card['test_balanced_accuracy'] = tasks['upper_body']['test_balanced_accuracy']
        card['test_confusion_matrix'] = tasks['upper_body']['test_confusion_matrix']
    (output / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    (output / 'training_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
    experiment['status'] = 'completed'
    (output / 'experiment.json').write_text(json.dumps(experiment, indent=2), encoding='utf-8')
    if output.name == 'sitting-posture-pilot-v1':
        (ROOT.parent / 'docs/SITTING_POSTURE_RESULTS.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    print(json.dumps({'tasks': tasks, 'clinical_approved': False}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--normalize-pose', action='store_true')
    parser.add_argument('--skip-test', action='store_true')
    args = parser.parse_args()
    main(args.epochs, args.output, args.normalize_pose, args.skip_test)
