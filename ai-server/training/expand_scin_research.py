"""Acquire high-consensus source cases without reassigning existing validation/test cases."""
import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fetch_scin import ROOT, fetch
from prepare_scin_research import eligible_cases
from skin_data_audit import find_near_duplicates, image_fingerprints
from train_skin_research import validate_splits


def run(output):
    if output.exists():
        raise ValueError('Use a new manifest destination; existing cohorts are immutable')
    directory = ROOT / 'datasets/scin'
    previous_path = directory / 'research_manifest.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8'))
    if previous.get('clinical_ready') is not False:
        raise ValueError('Explicit research-only source cohort required')
    records = []
    for row in previous['records']:
        fingerprint = image_fingerprints(directory / row['path'])
        if fingerprint['sha256'] != row['sha256']:
            raise ValueError('Existing SCIN image changed after its original audit')
        records.append({**row, **fingerprint})
    validate_splits(records, 'case_id')
    old_cases = {row['case_id'] for row in records}
    candidates = [row for row in eligible_cases(directory) if row['case_id'] not in old_cases]

    def acquire(row):
        name = hashlib.sha256((row['case_id'] + row['source']).encode()).hexdigest()[:24] + '.jpg'
        relative = 'images/' + name
        fetch(row['source'], directory / relative)
        return {**row, 'path': relative, 'split': 'train', **image_fingerprints(directory / relative)}

    with ThreadPoolExecutor(max_workers=4) as pool:
        new = []
        for row in pool.map(acquire, candidates):
            new.append(row)
            if len(new) % 20 == 0:
                print(f'Additional SCIN cases acquired {len(new)}/{len(candidates)}', flush=True)
    all_rows = records + new
    # Existing held-out cases stay held out. Never silently turn a test case into training data.
    exact_seen = {row['pixel_sha256'] for row in records}
    retained, quarantine = [], []
    for row in new:
        if row['pixel_sha256'] in exact_seen:
            quarantine.append({**row, 'reason': 'exact_duplicate_of_existing_cohort_or_new_case'})
        else:
            exact_seen.add(row['pixel_sha256'])
            retained.append(row)
    near = find_near_duplicates(all_rows)
    # The auditor's pair schema is checked explicitly before choosing a quarantine policy.
    old_count = len(records)
    rejected = set()
    by_path = {row['path']: row for row in all_rows}
    old_paths = {row['path'] for row in records}
    for pair in near:
        first, second = pair['left'], pair['right']
        # Paths, not labels, identify an image; no clinical interpretation is inferred.
        a, b = by_path[first], by_path[second]
        if a['split'] != b['split']:
            if first in old_paths and second in old_paths:
                raise ValueError('Existing cohort has cross-split near duplicates; review before expansion')
            rejected.update(r['path'] for r in (a, b) if r['case_id'] not in old_cases)
    accepted = records + [row for row in retained if row['path'] not in rejected]
    quarantine.extend({**r, 'reason': 'cross_split_near_duplicate_requires_review'} for r in retained if r['path'] in rejected)
    manifest = {**previous, 'records': accepted,
        'parent_manifest_sha256': hashlib.sha256(previous_path.read_bytes()).hexdigest(),
        'expansion_policy': 'Preserve original case assignments; new high-consensus cases train only',
        'commercial_release_allowed': False, 'patient_identity_verified': False,
        'additional_training_cases': len(accepted) - old_count, 'quarantine': quarantine,
        'limitations': previous.get('limitations', []) + ['New images predominantly eczema; imbalance remains.',
            'Existing validation/test reused; no new independent patient test established.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    summary = {'source': 'https://github.com/google-research-datasets/scin',
        'parent_manifest_sha256': manifest['parent_manifest_sha256'], 'new_training_cases': len(accepted) - old_count,
        'quarantined_new_images': len(quarantine), 'total_images': len(accepted),
        'class_counts': dict(Counter(r['label'] for r in accepted)),
        'split_counts': dict(Counter(r['split'] for r in accepted)), 'old_assignments_preserved': True,
        'clinical_approved': False, 'patient_identity_verified': False, 'commercial_release_allowed': False}
    output.with_name(output.stem + '_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'datasets/scin/expanded_manifest_20261025.json')
    args = parser.parse_args()
    run(args.output)
