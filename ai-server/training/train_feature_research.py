"""Fixed-split, validation-selected feature baselines. Never reads test image bytes."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch import nn
from torchvision.models import MobileNet_V3_Small_Weights, ResNet18_Weights, mobilenet_v3_small, resnet18

from train_medical_pilots import ROOT, checked_path
from train_skin_research import validate_splits


def color_features(image):
    """Raw appearance descriptors; deliberately no fabricated color calibration."""
    rgb = np.asarray(image.convert('RGB').resize((128, 128)), dtype=np.uint8)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32) / 255
    rgb = rgb.astype(np.float32) / 255
    values = []
    for array in (rgb, lab):
        for region in (array, array[32:96, 32:96]):
            flat = region.reshape(-1, 3)
            values.extend(flat.mean(0))
            values.extend(flat.std(0))
            values.extend(np.quantile(flat, [.1, .5, .9], axis=0).reshape(-1))
    return np.asarray(values, dtype=np.float32)


def inputs(task):
    if task == 'tongue_appearance':
        base = ROOT / 'datasets/original/tongue_coating_zenodo_20970467'
        directory = base / 'raw'
        manifest_path = base / 'appearance_manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('clinical_ready') is not False or manifest.get('source_class_map_verified') is not True or manifest.get('research_only') is not True:
            raise ValueError('Audited source-labelled appearance research manifest required')
        identity = 'augmentation_family'
    elif task in ('skin', 'scin'):
        directory = ROOT / ('datasets/kaggle/skindisnet_3_v1' if task == 'skin' else 'datasets/scin')
        manifest_path = directory / ('research_patient_manifest.json' if task == 'skin' else 'expanded_manifest_20261025.json')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('clinical_ready') is not False or (task == 'skin' and not manifest.get('patient_mapping_complete')):
            raise ValueError('Explicit audited research grouping is required')
        identity = 'patient_group' if task == 'skin' else 'case_id'
    else:
        names = {'anemia': ('anemia-conjunctiva-pilot-v1', 'cp_anemic_v1'),
                 'eye': ('eye-conjunctivitis-pilot-v1', 'eye_conjunctivitis_alisofiya_v1'),
                 'retina': ('retina-fundus-pilot-v1', 'retina_eye_classification_v1')}
        model, dataset = names[task]
        initial = ROOT / 'models/research' / model
        card = json.loads((initial / 'model_card.json').read_text(encoding='utf-8'))
        if card.get('clinical_approved') is not False:
            raise ValueError('Research-only starting evidence required')
        manifest_path = initial / 'experiment_manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        directory = ROOT / 'datasets/kaggle' / dataset / 'raw'
        identity = 'sha256'
    splits = validate_splits(manifest['records'], identity)
    return directory, manifest_path, splits, identity


def select_classifier(features, targets, validation, truth, classes):
    history, best = [], None
    # Predeclared modest grid; selection uses only existing validation observations.
    for regularization in (.01, .1, 1., 10.):
        classifier = make_pipeline(StandardScaler(), LogisticRegression(
            C=regularization, class_weight='balanced', max_iter=2000, random_state=42))
        classifier.fit(features, targets)
        predictions = classifier.predict(validation)
        score = float(balanced_accuracy_score(truth, predictions))
        history.append({'C': regularization, 'validation_balanced_accuracy': score})
        if best is None or score > best[0]:
            best = (score, classifier, predictions, regularization)
    score, classifier, predictions, regularization = best
    report = {'validation_balanced_accuracy': score, 'selected_C': regularization,
        'validation_confusion_matrix': confusion_matrix(truth, predictions, labels=list(range(len(classes)))).tolist(),
        'validation_report': classification_report(truth, predictions, labels=list(range(len(classes))),
            target_names=classes, output_dict=True, zero_division=0), 'candidates': history}
    return classifier, report


def run(task, output, backbone_name='mobilenet'):
    if output.exists():
        raise ValueError('Use a new immutable experiment directory')
    torch.set_num_threads(2)
    torch.manual_seed(42)
    directory, manifest_path, splits, identity = inputs(task)
    classes = sorted({r['label'] for split in splits.values() for r in split})
    filename = 'mobilenet_v3_small-047dcff4.pth' if backbone_name == 'mobilenet' else 'resnet18-f37072fd.pth'
    weights = ROOT / 'models/pretrained' / filename
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()
    if not digest.startswith('047dcff4' if backbone_name == 'mobilenet' else 'f37072fd'):
        raise ValueError('Official backbone integrity mismatch')
    backbone = mobilenet_v3_small(weights=None) if backbone_name == 'mobilenet' else resnet18(weights=None)
    backbone.load_state_dict(torch.load(weights, weights_only=True, map_location='cpu'))
    if backbone_name == 'mobilenet':
        backbone.classifier = nn.Identity()
    else:
        backbone.fc = nn.Identity()
    backbone.eval()
    transform = (MobileNet_V3_Small_Weights.DEFAULT if backbone_name == 'mobilenet' else ResNet18_Weights.DEFAULT).transforms()
    cache = {}
    output.mkdir(parents=True)
    experiment = {'task': task, 'status': 'running', 'seed': 42, 'test_evaluated': False,
        'clinical_approved': False, 'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
    (output / 'experiment.json').write_text(json.dumps(experiment, indent=2), encoding='utf-8')
    for split in ('train', 'val'):
        cnn, color, labels = [], [], []
        rows = splits[split]
        for offset in range(0, len(rows), 16):
            images = []
            for row in rows[offset:offset + 16]:
                path = checked_path(directory, row['path'], row['sha256'])
                with Image.open(path) as source:
                    if source.width * source.height > 25_000_000:
                        raise ValueError('Image exceeds pixel budget')
                    image = ImageOps.exif_transpose(source).convert('RGB')
                    images.append(transform(image))
                    color.append(color_features(image))
                labels.append(classes.index(row['label']))
            with torch.inference_mode():
                cnn.append(backbone(torch.stack(images)).numpy())
            print(f'{task}: {split} features {min(offset + 16, len(rows))}/{len(rows)}', flush=True)
        cache[split] = (np.concatenate(cnn), np.stack(color), np.asarray(labels))
    candidates, fitted = {}, {}
    for mode in ('cnn', 'color', 'cnn_color'):
        def features(split):
            cnn, color, _ = cache[split]
            return cnn if mode == 'cnn' else color if mode == 'color' else np.concatenate((cnn, color), axis=1)
        classifier, report = select_classifier(features('train'), cache['train'][2],
            features('val'), cache['val'][2], classes)
        candidates[mode] = report
        fitted[mode] = classifier
    selected = max(candidates, key=lambda mode: candidates[mode]['validation_balanced_accuracy'])
    classifier = fitted[selected]
    scaler, regression = classifier.steps[0][1], classifier.steps[1][1]
    # Store plain numeric state instead of an executable pickle estimator.
    state = {'scaler_mean': torch.tensor(scaler.mean_), 'scaler_scale': torch.tensor(scaler.scale_),
        'coefficients': torch.tensor(regression.coef_), 'intercept': torch.tensor(regression.intercept_),
        'classes': torch.tensor(regression.classes_)}
    torch.save(state, output / 'weights.pt')
    card = {'model': output.name, 'architecture': 'FrozenImageNetColorRegularizedFeatures', 'task': task,
        'backbone': backbone_name, 'selected_features': selected, 'classes': classes,
        'feature_candidates': candidates, **candidates[selected],
        'pretrained_sha256': digest, 'manifest_sha256': experiment['manifest_sha256'],
        'checkpoint_sha256': hashlib.sha256((output / 'weights.pt').read_bytes()).hexdigest(),
        'split_counts': {s: len(rows) for s, rows in splits.items()}, 'split_identity': identity,
        'patient_identity_verified': False, 'test_evaluated': False, 'clinical_approved': False,
        'commercial_release_allowed': False, 'release_status': 'research_only_validation_selected',
        'limitations': ['Existing validation reused to select feature mode and regularization; optimistic selection score.',
            'Test image bytes never loaded; no new independent or external clinical performance established.',
            'Patient identity, clinical reference labels and commercial source rights require review.',
            'Raw color descriptors are lighting/device sensitive and are not color calibration.']}
    (output / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    experiment['status'] = 'completed'
    (output / 'experiment.json').write_text(json.dumps(experiment, indent=2), encoding='utf-8')
    print(json.dumps({'model': output.name, 'validation_balanced_accuracy': card['validation_balanced_accuracy'],
        'selected_features': selected, 'test_evaluated': False}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=['skin', 'scin', 'anemia', 'eye', 'retina', 'tongue_appearance'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backbone', choices=['mobilenet', 'resnet18'], default='mobilenet')
    args = parser.parse_args()
    run(args.task, args.output, args.backbone)
