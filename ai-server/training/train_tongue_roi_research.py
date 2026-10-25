"""Fixed-split tongue appearance experiment using source polygons; no medical diagnosis."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import balanced_accuracy_score, classification_report, confusion_matrix

from audit_missing_labels import annotation_geometry
from train_feature_research import select_classifier
from train_medical_pilots import ROOT, checked_path
from train_skin_research import validate_splits


def roi_features(rgb, annotations, expected_class):
    rgb = np.asarray(rgb, dtype=np.uint8)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.shape[0] * rgb.shape[1] > 25_000_000:
        raise ValueError('Bounded RGB image required')
    rgb = cv2.resize(rgb, (192, 192), interpolation=cv2.INTER_AREA)
    mask = np.zeros((192, 192), dtype=np.uint8)
    for line in annotations.splitlines():
        if not line.strip():
            continue
        category, kind = annotation_geometry(line)
        if kind != 'polygon' or category != expected_class:
            raise ValueError('Ambiguous source annotation; do not infer a new label')
        points = np.asarray([float(v) for v in line.split()[1:]]).reshape(-1, 2)
        points = np.rint(points * 191).astype(np.int32)
        cv2.fillPoly(mask, [points], 255)
    selected = mask > 0
    if selected.sum() < 100:
        raise ValueError('Insufficient source region')
    values = []
    for array in (rgb, cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB), cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)):
        pixels = array[selected].astype(float) / 255
        values.extend(pixels.mean(0))
        values.extend(pixels.std(0))
        values.extend(np.quantile(pixels, [.1, .25, .5, .75, .9], axis=0).ravel())
        for channel in range(3):
            histogram = np.histogram(pixels[:, channel], bins=12, range=(0, 1))[0]
            values.extend(histogram / histogram.sum())
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    gradient = cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
    interior = cv2.erode(mask, np.ones((3, 3), np.uint8)) > 0
    if not interior.any():
        raise ValueError('Insufficient interior texture region')
    values.extend(np.quantile(gradient[interior], [.1, .25, .5, .75, .9]))
    return np.asarray(values, dtype=np.float32)


def forest_state(classifier):
    return [{name: torch.tensor(getattr(estimator.tree_, name))
             for name in ('children_left', 'children_right', 'feature', 'threshold', 'value')}
            for estimator in classifier.estimators_]


def forest_probabilities(features, trees):
    features = np.asarray(features, dtype=np.float32)
    probabilities = np.zeros((len(features), trees[0]['value'].shape[-1]))
    for tree in trees:
        tree = {key: np.asarray(value) for key, value in tree.items()}
        nodes = np.zeros(len(features), dtype=int)
        for _ in range(len(tree['feature'])):
            active = tree['children_left'][nodes] != -1
            if not active.any():
                break
            rows = np.flatnonzero(active)
            current = nodes[rows]
            go_left = features[rows, tree['feature'][current]] <= tree['threshold'][current]
            nodes[rows] = np.where(go_left, tree['children_left'][current], tree['children_right'][current])
        else:
            raise ValueError('Cyclic or invalid forest artifact')
        values = tree['value'][nodes, 0, :]
        probabilities += values / values.sum(axis=1, keepdims=True)
    return probabilities / len(trees)


def run(output, classifier_kind='logistic'):
    if output.exists():
        raise ValueError('Use a new immutable experiment output')
    directory = ROOT / 'datasets/original/tongue_coating_zenodo_20970467'
    manifest_path = directory / 'appearance_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('source_class_map_verified') is not True or manifest.get('research_only') is not True:
        raise ValueError('Audited appearance manifest required')
    archive_path = directory / 'images.zip'
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != 'acfead7112b7cb6e506028f74dead326b1c0ce31f598c67b5675ccfb09cf56d7':
        raise ValueError('Source archive changed')
    splits = validate_splits(manifest['records'], 'augmentation_family')
    classes = sorted({r['label'] for rows in splits.values() for r in rows})
    cache = {}
    with zipfile.ZipFile(archive_path) as archive:
        for split in ('train', 'val'):
            features, targets = [], []
            for index, row in enumerate(splits[split]):
                path = checked_path(directory / 'raw', row['path'], row['sha256'])
                annotation = str(Path(row['path']).with_suffix('.txt')).replace('\\', '/').replace('/images/', '/labels/')
                with Image.open(path) as image:
                    if image.getexif().get(274, 1) != 1:
                        raise ValueError('Review source polygon orientation before using transformed photos')
                    features.append(roi_features(np.asarray(image.convert('RGB')), archive.read(annotation).decode('utf-8-sig'), row['source_class_id']))
                targets.append(classes.index(row['label']))
                if (index + 1) % 500 == 0:
                    print(f'Tongue ROI {split}: {index + 1}/{len(splits[split])}', flush=True)
            cache[split] = np.stack(features), np.asarray(targets)
    output.mkdir(parents=True)
    np.savez_compressed(output / 'private_feature_cache.npz', train_features=cache['train'][0], train_labels=cache['train'][1],
        validation_features=cache['val'][0], validation_labels=cache['val'][1])
    if classifier_kind == 'extra_trees':
        # One predeclared nonlinear candidate; no test-set or hyperparameter search.
        classifier = ExtraTreesClassifier(n_estimators=400, max_depth=24, min_samples_leaf=3,
            max_features=.7, class_weight='balanced', random_state=42, n_jobs=2)
        classifier.fit(*cache['train'])
        predictions = classifier.predict(cache['val'][0])
        state = {'trees': forest_state(classifier), 'classes': torch.tensor(classifier.classes_)}
        torch.save(state, output / 'weights.pt')
        restored = torch.load(output / 'weights.pt', weights_only=True, map_location='cpu')
        restored_predictions = forest_probabilities(cache['val'][0], restored['trees']).argmax(axis=1)
        if not np.array_equal(restored_predictions, predictions):
            raise ValueError('Numeric forest artifact forward check failed')
        report = {'validation_balanced_accuracy': float(balanced_accuracy_score(cache['val'][1], predictions)),
            'validation_confusion_matrix': confusion_matrix(cache['val'][1], predictions, labels=list(range(len(classes)))).tolist(),
            'validation_report': classification_report(cache['val'][1], predictions, target_names=classes, output_dict=True, zero_division=0),
            'safe_checkpoint_forward_verified': True,
            'parameters': {'trees': 400, 'max_depth': 24, 'min_samples_leaf': 3, 'max_features': .7}}
    else:
        classifier, report = select_classifier(*cache['train'], *cache['val'], classes)
        scaler, regression = classifier.steps[0][1], classifier.steps[1][1]
        torch.save({'scaler_mean': torch.tensor(scaler.mean_), 'scaler_scale': torch.tensor(scaler.scale_),
            'coefficients': torch.tensor(regression.coef_), 'intercept': torch.tensor(regression.intercept_),
            'classes': torch.tensor(regression.classes_)}, output / 'weights.pt')
    card = {'model': output.name, 'architecture': 'SourcePolygonAppearanceFeatures', 'classifier': classifier_kind, 'task': 'tongue_appearance',
        'classes': classes, **report, 'split_counts': {s: len(v) for s, v in splits.items()},
        'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'checkpoint_sha256': hashlib.sha256((output / 'weights.pt').read_bytes()).hexdigest(),
        'feature_count': int(cache['train'][0].shape[1]), 'test_evaluated': False,
        'clinical_approved': False, 'deployment_authorized': False, 'patient_identity_verified': False,
        'annotation_required_at_inference': True, 'release_status': 'research_only',
        'limitations': ['Source polygons are supplied, not predicted: this is not end-to-end live detection.',
            'Appearance/color categories are not disease or organ diagnoses.',
            'Validation reused for regularization/experiment selection; score may be optimistic.',
            'Export-family grouping is not verified patient grouping; external test not performed.']}
    (output / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    print(json.dumps({k: card[k] for k in ('model', 'validation_balanced_accuracy', 'test_evaluated', 'clinical_approved')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--classifier', choices=('logistic', 'extra_trees'), default='logistic')
    args = parser.parse_args()
    run(args.output, args.classifier)
