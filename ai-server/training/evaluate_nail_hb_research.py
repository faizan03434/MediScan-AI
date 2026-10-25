"""Consume a frozen internal test once; never fit parameters or authorize diagnosis."""
import argparse
import csv
import hashlib
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from acquire_hb_reference import ROOT, SHA256
from train_medical_pilots import checked_path
from train_nail_hb_research import boxes, hemoglobin_g_dl, region_features


def evaluate(run):
    output = run / 'internal_test_report.json'
    if output.exists():
        raise ValueError('This internal test is already consumed; do not overwrite or tune against it')
    card_path, manifest_path, weights = run / 'model_card.json', run / 'private_manifest.json', run / 'weights.pt'
    card = json.loads(card_path.read_text(encoding='utf-8'))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if card.get('architecture') != 'SourceBoxColorRidgeRegression' or card.get('clinical_approved') is not False:
        raise ValueError('Frozen research Hb regressor required')
    if hashlib.sha256(weights.read_bytes()).hexdigest() != card['checkpoint_sha256'] or manifest['source_sha256'] != SHA256:
        raise ValueError('Frozen checkpoint/source identity mismatch')
    original = ROOT / 'datasets/original/hb_figshare_25867432'
    archive_path, raw = original / 'data.zip', original / 'raw'
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Original archive integrity failed')
    metadata_path = next(raw.rglob('metadata.csv'))
    if hashlib.sha256(metadata_path.read_bytes()).hexdigest() != manifest['metadata_sha256']:
        raise ValueError('Source Hb metadata changed')
    with zipfile.ZipFile(archive_path) as archive:
        if archive.read(metadata_path.relative_to(raw).as_posix()) != metadata_path.read_bytes():
            raise ValueError('Metadata differs from original archive')
    with metadata_path.open(encoding='utf-8-sig', newline='') as handle:
        source_rows = list(csv.DictReader(handle))
    provider = {r['PATIENT_ID'].strip(): r for r in source_rows}
    if len(provider) != len(source_rows):
        raise ValueError('Ambiguous provider reference identity')
    subjects, groups, images = {}, {}, set()
    for row in manifest['records']:
        subject, split = row['subject_pseudonym'], row['split']
        group = row.get('near_duplicate_group', subject)
        if split not in {'train', 'val', 'test'} or subject in subjects or row['sha256'] in images:
            raise ValueError('Repeated subject/image or invalid split in frozen experiment')
        if group in groups and groups[group] != split:
            raise ValueError('Near-match group crosses reserved splits')
        source_id = Path(row['path']).stem
        if source_id not in provider or subject != hashlib.sha256(('figshare:25867432:' + source_id).encode()).hexdigest():
            raise ValueError('Source patient-to-photo mapping changed')
        if row['hb_g_dl'] != hemoglobin_g_dl(provider[source_id]['HB_LEVEL_GperL']):
            raise ValueError('Frozen target no longer matches original measured Hb')
        subjects[subject], groups[group] = split, split
        images.add(row['sha256'])
    test = [r for r in manifest['records'] if r['split'] == 'test']
    if not test:
        raise ValueError('No reserved test cases')
    state = torch.load(weights, weights_only=True, map_location='cpu')
    features, truth = [], []
    for record in test:
        path = checked_path(raw, record['path'], record['sha256'])
        source = provider[path.stem]
        with Image.open(path) as image:
            if image.getexif().get(274, 1) != 1:
                raise ValueError('Unreviewed source-box orientation')
            rgb = np.asarray(image.convert('RGB'))
            nail = region_features(rgb, boxes(source['NAIL_BOUNDING_BOXES'], image.width, image.height))
            skin = region_features(rgb, boxes(source['SKIN_BOUNDING_BOXES'], image.width, image.height))
        features.append(np.concatenate((nail, skin, nail - skin)))
        truth.append(record['hb_g_dl'])
    predicted = ((np.stack(features) - np.asarray(state['scaler_mean'])) / np.asarray(state['scaler_scale'])) @ np.asarray(state['coefficients']) + float(state['intercept'])
    error = predicted - np.asarray(truth)
    if not np.isfinite(error).all():
        raise ValueError('Non-finite frozen model outputs')
    clusters = defaultdict(list)
    for index, row in enumerate(test):
        clusters[row.get('near_duplicate_group', row['subject_pseudonym'])].append(index)
    cluster_rows = list(clusters.values())
    rng = np.random.default_rng(42)
    bootstrap = [float(np.abs(error[np.concatenate([cluster_rows[i] for i in rng.integers(0, len(cluster_rows), len(cluster_rows))])]).mean()) for _ in range(2000)]
    train_mean = np.mean([r['hb_g_dl'] for r in manifest['records'] if r['split'] == 'train'])
    report = {'model': card['model'], 'task': 'nail_hb_regression', 'evaluation_scope': 'internal_provider_site_only',
        'checkpoint_sha256': card['checkpoint_sha256'], 'model_card_sha256': hashlib.sha256(card_path.read_bytes()).hexdigest(),
        'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(), 'source_sha256': SHA256,
        'test_subject_records': len(test), 'test_near_match_groups': len(cluster_rows),
        'test_mae_g_dl': float(np.abs(error).mean()), 'test_rmse_g_dl': float(math.sqrt(np.square(error).mean())),
        'test_mean_signed_error_g_dl': float(error.mean()),
        'training_mean_baseline_test_mae_g_dl': float(np.abs(np.asarray(truth) - train_mean).mean()),
        'test_mae_cluster_bootstrap_95_interval_g_dl': np.quantile(bootstrap, [.025, .975]).tolist(),
        'clinical_approved': False, 'deployment_authorized': False, 'external_test': False,
        'parameters_fitted_on_test': False, 'test_consumed': True,
        'limitations': ['Approximate interval resamples near-match groups; independently authenticated patient/site sampling is not established.',
            'This inspected internal test must not guide further tuning; reserve a fresh external cohort.',
            'Hb regression with supplied source boxes is not live anemia diagnosis or a classification accuracy percentage.']}
    with output.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    evaluate(parser.parse_args().run)
