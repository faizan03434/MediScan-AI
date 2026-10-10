"""Local ZIP intake with unverified provenance; never executes archive contents."""
import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from acquire_skin_kaggle import safe_extract, sha256  # noqa: E402 - direct script entry point
from clean_medical_intake import select_clean  # noqa: E402
from skin_data_audit import audit, find_near_duplicates  # noqa: E402


def intake(archive, name, target_labels=None):
    directory = ROOT / 'datasets/user_uploads' / name
    directory.mkdir(parents=True, exist_ok=True)
    digest = sha256(archive)
    target = directory / 'source.zip'
    if target.exists():
        if sha256(target) != digest:
            raise ValueError('Existing intake contains a different ZIP; use a new name')
    else:
        shutil.copyfile(archive, target)
    extracted = safe_extract(target, directory / 'raw', max_expanded=1024 * 1024 * 1024)
    receipt = {'archive_sha256': digest, 'archive_bytes': target.stat().st_size,
               'extracted_members': extracted, 'acquired_at': datetime.now(timezone.utc).isoformat(),
               'provenance': 'User downloaded from Kaggle; exact page URL pending',
               'license_verified': False, 'patient_mapping_verified': False,
               'training_ready': False, 'clinical_ready': False, 'commercial_ready': False}
    (directory / 'acquisition.json').write_text(json.dumps(receipt, indent=2))
    print(name, 'extracted', extracted, 'files; auditing...', flush=True)
    report = audit(directory / 'raw', directory / 'audit')
    rows = [json.loads(line) for line in (directory / 'audit/image_index.jsonl').read_text().splitlines() if line]
    existing = []
    sources = {'ghana_fingernails': ROOT / 'datasets/kaggle/ghana_fingernails_v1/audit/image_index.jsonl',
               'cp_anemic': ROOT / 'datasets/kaggle/cp_anemic_v1/audit/image_index.jsonl',
               'skindisnet': ROOT / 'datasets/kaggle/skindisnet_3_v1/audit/image_index.jsonl',
               'scin': ROOT / 'datasets/scin/expansion_audit/image_index.jsonl'}
    for source, path in sources.items():
        for line in path.read_text().splitlines():
            if line:
                row = json.loads(line)
                existing.append({**row, 'path': source + ':' + row['path'], 'source': source})
    existing_by_hash = {}
    for row in existing:
        existing_by_hash.setdefault(row['pixel_sha256'], []).append(row['source'])
    unique_existing = {row['pixel_sha256']: row for row in existing}
    unique_new = {row['pixel_sha256']: {**row, 'path': 'new:' + row['path']} for row in rows}
    cross_near = [pair for pair in find_near_duplicates(list(unique_existing.values()) + list(unique_new.values()))
                  if pair['left'].startswith('new:') != pair['right'].startswith('new:')]
    issues = {}
    for row in rows:
        reasons = set()
        if row['pixel_sha256'] in existing_by_hash:
            reasons.add('already_present_in_existing_source')
        if target_labels is None:
            reasons.add('no_clinical_labels_or_augmentation_lineage')
        elif row['label'] not in target_labels:
            reasons.add('outside_current_common_skin_scope')
        if reasons:
            issues[row['path']] = reasons
    for pair in cross_near:
        for path in (pair['left'], pair['right']):
            if path.startswith('new:'):
                issues.setdefault(path[4:], set()).add('cross_source_near_match_requires_review')
    accepted, quarantine, redundant = select_clean(
        rows, issues, json.loads((directory / 'audit/near_duplicates.json').read_text()))
    overlap = {'assets_already_present': sum(row['pixel_sha256'] in existing_by_hash for row in rows),
               'unique_pixels_already_present': len(set(unique_new) & set(existing_by_hash)),
               'cross_source_near_candidate_pairs': len(cross_near),
               'source_overlap_unique_pixels': {source: sum(source in existing_by_hash.get(digest, []) for digest in unique_new)
                                                for source in sources}}
    summary = {**receipt, 'audit': report, 'overlap': overlap,
               'candidate_unique_images': len(accepted),
               'candidate_folder_counts': dict(Counter(row['label'] for row in accepted)),
               'quarantined_assets': len(quarantine), 'redundant_consistent_copies': len(redundant),
               'labels_are_folder_names_not_verified_diagnoses': True}
    (directory / 'research_candidate_manifest.json').write_text(json.dumps({
        **summary, 'records': accepted, 'quarantine': quarantine, 'redundant': redundant}, indent=2))
    (directory / 'cross_source_near_candidates.json').write_text(json.dumps(cross_near, indent=2))
    (directory / 'intake_summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def refresh_candidate_view(directory):
    """Apply current group-exclusion rules to already completed local audit outputs."""
    manifest_path = directory / 'research_candidate_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    rows = [json.loads(line) for line in (directory / 'audit/image_index.jsonl').read_text().splitlines() if line]
    issues = {row['path']: set(row['reasons']) for row in manifest['quarantine']}
    accepted, quarantine, redundant = select_clean(
        rows, issues, json.loads((directory / 'audit/near_duplicates.json').read_text()))
    summary = json.loads((directory / 'intake_summary.json').read_text())
    summary.update(candidate_unique_images=len(accepted),
                   candidate_folder_counts=dict(Counter(row['label'] for row in accepted)),
                   quarantined_assets=len(quarantine), redundant_consistent_copies=len(redundant))
    manifest_path.write_text(json.dumps({**summary, 'records': accepted, 'quarantine': quarantine,
                                         'redundant': redundant}, indent=2))
    (directory / 'intake_summary.json').write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--nails', type=Path)
    parser.add_argument('--skin', type=Path)
    parser.add_argument('--refresh-only', action='store_true')
    args = parser.parse_args()
    if args.refresh_only:
        print(json.dumps({name: refresh_candidate_view(ROOT / 'datasets/user_uploads' / name)
                          for name in ('user_fingernails_20261004', 'user_skin_20261004')}, indent=2))
    elif args.nails and args.skin:
        intake(args.nails, 'user_fingernails_20261004')
        intake(args.skin, 'user_skin_20261004', {'Acne', 'Eczema Photos', 'Tinea Ringworm Candidiasis and other Fungal Infections'})
    else:
        parser.error('Provide both ZIP paths or --refresh-only for completed intakes')
