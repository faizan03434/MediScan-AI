"""Patient-grouped Hb regression from a pinned source; not an anemia diagnostic model."""
import argparse
import ast
import csv
import hashlib
import json
import math
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from acquire_hb_reference import MD5, SHA256, SOURCE, ROOT
from skin_data_audit import find_near_duplicates, image_fingerprints


def hemoglobin_g_dl(value):
    # The source's explicit HB_LEVEL_GperL field is g/L, not g/dL.
    result = float(value) / 10
    if not math.isfinite(result) or not 0 < result < 30:
        raise ValueError('Invalid provider Hb value in g/L')
    return result


def boxes(value, width, height):
    if not isinstance(value, str) or len(value) > 10000:
        raise ValueError('Bounded source box list required')
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, list) or len(parsed) != 3:
        raise ValueError('Three provider finger regions required')
    result = []
    for box in parsed:
        if not isinstance(box, list) or len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box):
            raise ValueError('Finite top/left/bottom/right boxes required')
        top, left, bottom, right = box
        if not 0 <= top < bottom <= height or not 0 <= left < right <= width:
            raise ValueError('Source region outside image; review coordinates rather than silently clipping')
        result.append((int(top), int(left), int(bottom), int(right)))
    return result


def region_features(rgb, regions):
    features = []
    for top, left, bottom, right in regions:
        crop = rgb[top:bottom, left:right]
        if not crop.size:
            raise ValueError('Empty source crop')
        crop = cv2.resize(crop, (48, 48), interpolation=cv2.INTER_AREA)
        description = []
        for data in (crop, cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)):
            pixels = data.reshape(-1, 3).astype(float) / 255
            description.extend(pixels.mean(0))
            description.extend(pixels.std(0))
            description.extend(np.quantile(pixels, [.1, .5, .9], axis=0).ravel())
        features.append(description)
    return np.asarray(features).mean(axis=0)


def grouped_splits(records, near, previous):
    by_path = {r['path']: r for r in records}
    parents = {path: path for path in by_path}

    def root(path):
        while parents[path] != path:
            parents[path] = parents[parents[path]]
            path = parents[path]
        return path

    for pair in near:
        left, right = root(pair['left']), root(pair['right'])
        parents[max(left, right)] = min(left, right)
    groups = defaultdict(list)
    for record in records:
        groups[root(record['path'])].append(record)
    retained, quarantined = [], set()
    for group in groups.values():
        prior = {previous[r['path']] for r in group if r['path'] in previous}
        if len(prior) > 1:
            quarantined.update(r['path'] for r in group)
            continue
        identity = hashlib.sha256(':'.join(sorted(r['subject_pseudonym'] for r in group)).encode()).hexdigest()
        number = int(hashlib.sha256(('near-group42:' + identity).encode()).hexdigest(), 16) % 100
        split = next(iter(prior)) if prior else 'train' if number < 70 else 'val' if number < 85 else 'test'
        if split not in {'train', 'val', 'test'}:
            raise ValueError('Invalid previous split')
        for record in group:
            record.update(split=split, near_duplicate_group=identity)
            retained.append(record)
    return retained, quarantined


def run(output, baseline_manifest=None):
    if output.exists():
        raise ValueError('Use a new immutable experiment output')
    directory = ROOT / 'datasets/original/hb_figshare_25867432'
    archive_path = directory / 'data.zip'
    if hashlib.md5(archive_path.read_bytes()).hexdigest() != MD5 or hashlib.sha256(archive_path.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Pinned original archive identity required before training')
    raw = directory / 'raw'
    metadata_paths = list(raw.rglob('metadata.csv'))
    if len(metadata_paths) != 1:
        raise ValueError('Unique original metadata.csv required')
    metadata_path = metadata_paths[0]
    with metadata_path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    required = {'PATIENT_ID', 'HB_LEVEL_GperL', 'NAIL_BOUNDING_BOXES', 'SKIN_BOUNDING_BOXES'}
    if not rows or not required.issubset(rows[0]):
        raise ValueError('Original provider columns missing; inspect source schema')
    photos = defaultdict(list)
    for photo in raw.rglob('*.jpg'):
        photos[photo.stem].append(photo)
    records, seen_subjects = [], set()
    with zipfile.ZipFile(archive_path) as archive:
        if archive.read(metadata_path.relative_to(raw).as_posix()) != metadata_path.read_bytes():
            raise ValueError('Extracted provider metadata changed')
        for row in rows:
            subject = row['PATIENT_ID'].strip()
            if not subject or subject in seen_subjects or len(photos[subject]) != 1:
                raise ValueError('Ambiguous subject-to-image mapping; no fabricated subject identity')
            seen_subjects.add(subject)
            photo = photos[subject][0]
            relative = photo.relative_to(raw).as_posix()
            if archive.read(relative) != photo.read_bytes():
                raise ValueError('Extracted source image changed')
            hb = hemoglobin_g_dl(row['HB_LEVEL_GperL'])
            records.append({'subject_pseudonym': hashlib.sha256(('figshare:25867432:' + subject).encode()).hexdigest(),
                'path': relative, 'label': str(hb), 'hb_g_dl': hb, 'provider_row': row, **image_fingerprints(photo)})
    duplicate_groups = defaultdict(list)
    for record in records:
        duplicate_groups[record['pixel_sha256']].append(record)
    excluded = {r['path'] for group in duplicate_groups.values() if len(group) > 1 for r in group}
    near = find_near_duplicates(records)
    if baseline_manifest:
        baseline = json.loads(baseline_manifest.read_text(encoding='utf-8'))
        if baseline.get('source_sha256') != SHA256 or baseline.get('metadata_sha256') != hashlib.sha256(metadata_path.read_bytes()).hexdigest():
            raise ValueError('Previous split belongs to a different original source')
        current = {r['path']: r for r in records}
        previous = {}
        for row in baseline['records']:
            if row['path'] not in current or any(row.get(key) != current[row['path']].get(key) for key in ('subject_pseudonym', 'sha256', 'hb_g_dl')):
                raise ValueError('Previous split identity/reference changed')
            previous[row['path']] = row['split']
        eligible = [r for r in records if r['path'] not in excluded]
        eligible_paths = {r['path'] for r in eligible}
        eligible_near = [p for p in near if p['left'] in eligible_paths and p['right'] in eligible_paths]
        retained, collisions = grouped_splits(eligible, eligible_near, previous)
        excluded.update(collisions)
    else:
        excluded.update(p[name] for p in near for name in ('left', 'right'))
        retained = [r for r in records if r['path'] not in excluded]
        # Stable subject-only ordering, independent of Hb labels and image appearance.
        retained.sort(key=lambda r: hashlib.sha256(('split42:' + r['subject_pseudonym']).encode()).hexdigest())
        first, second = int(.7 * len(retained)), int(.85 * len(retained))
        for index, record in enumerate(retained):
            record['split'] = 'train' if index < first else 'val' if index < second else 'test'
    if len(retained) < 100 or sum(r['split'] == 'train' for r in retained) < 60:
        raise ValueError('Insufficient independent retained references for this small research experiment')
    manifest = {'source': SOURCE, 'declared_license': 'CC0-1.0', 'source_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        'metadata_sha256': hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        'baseline_manifest_sha256': hashlib.sha256(baseline_manifest.read_bytes()).hexdigest() if baseline_manifest else None,
        'records': [{k: v for k, v in r.items() if k != 'provider_row'} for r in retained],
        'excluded_images': sorted(excluded), 'near_duplicate_candidate_pairs': near,
        'split_identity': 'provider_patient_id_not_independently_authenticated', 'clinical_approved': False}
    output.mkdir(parents=True)
    (output / 'private_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    cache = {}
    for split in ('train', 'val'):
        features, labels = [], []
        for record in retained:
            if record['split'] != split:
                continue
            with Image.open(raw / record['path']) as image:
                if image.getexif().get(274, 1) != 1:
                    raise ValueError('Review provider box orientation before transforming image')
                rgb = np.asarray(image.convert('RGB'))
                row = record['provider_row']
                nail = region_features(rgb, boxes(row['NAIL_BOUNDING_BOXES'], image.width, image.height))
                skin = region_features(rgb, boxes(row['SKIN_BOUNDING_BOXES'], image.width, image.height))
            features.append(np.concatenate((nail, skin, nail - skin)))
            labels.append(record['hb_g_dl'])
        cache[split] = np.stack(features), np.asarray(labels)
    candidates, best = [], None
    for alpha in (.1, 1., 10., 100.):
        fitted = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(*cache['train'])
        predicted = fitted.predict(cache['val'][0])
        score = float(mean_absolute_error(cache['val'][1], predicted))
        candidates.append({'alpha': alpha, 'validation_mae_g_dl': score})
        if best is None or score < best[0]:
            best = score, fitted, predicted, alpha
    score, fitted, predicted, alpha = best
    scaler, regression = fitted.steps[0][1], fitted.steps[1][1]
    torch.save({'scaler_mean': torch.tensor(scaler.mean_), 'scaler_scale': torch.tensor(scaler.scale_),
        'coefficients': torch.tensor(regression.coef_), 'intercept': torch.tensor(float(regression.intercept_))}, output / 'weights.pt')
    state = torch.load(output / 'weights.pt', weights_only=True, map_location='cpu')
    verified = ((cache['val'][0] - np.asarray(state['scaler_mean'])) / np.asarray(state['scaler_scale'])) @ np.asarray(state['coefficients']) + float(state['intercept'])
    if not np.allclose(verified, predicted, atol=1e-5):
        raise ValueError('Saved numeric model forward check failed')
    card = {'model': output.name, 'task': 'nail_hb_regression', 'architecture': 'SourceBoxColorRidgeRegression',
        'source': SOURCE, 'declared_license': 'CC0-1.0', 'provider_hb_unit': 'g/L', 'target_unit': 'g/dL',
        'near_duplicate_policy': 'connected_components_preserve_previous_splits' if baseline_manifest else 'quarantine_candidates',
        'original_rows': len(rows), 'retained_subjects': len(retained), 'excluded_images': len(excluded),
        'near_duplicate_candidate_pairs': len(near), 'split_counts': dict(Counter(r['split'] for r in retained)),
        'selected_alpha': alpha, 'candidates': candidates, 'validation_mae_g_dl': score,
        'validation_rmse_g_dl': float(math.sqrt(mean_squared_error(cache['val'][1], predicted))),
        'training_mean_baseline_validation_mae_g_dl': float(mean_absolute_error(cache['val'][1], np.full(len(predicted), cache['train'][1].mean()))),
        'checkpoint_sha256': hashlib.sha256((output / 'weights.pt').read_bytes()).hexdigest(),
        'source_sha256': manifest['source_sha256'], 'safe_checkpoint_forward_verified': True,
        'clinical_approved': False, 'deployment_authorized': False, 'test_evaluated': False,
        'patient_identity_verified': False, 'annotation_required_at_inference': True,
        'limitations': ['Continuous Hb research only; no anemia diagnosis assigned without clinical context.',
            'Source patient IDs and lab references are provider assertions, not independently authenticated reports.',
            'Age/sex are withheld; dates hashed; no Pakistan/external/device validation.',
            'Source nail/skin boxes are supplied, not predicted; not end-to-end live detection.',
            'Validation selects regularization and is optimistic; reserved test features were not loaded.']}
    (output / 'model_card.json').write_text(json.dumps(card, indent=2), encoding='utf-8')
    print(json.dumps(card), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-manifest', type=Path, help='Preserve existing splits and group newly eligible near-match candidates together')
    args = parser.parse_args()
    run(args.output, args.baseline_manifest)
