"""Non-destructive reviewed-data views. Unresolved identity/rights block training."""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
import numpy as np
from PIL import Image

from training.audit_anemia_metadata import normalized_id
from training.skin_data_audit import find_near_duplicates, image_fingerprints

ROOT = Path(__file__).resolve().parents[1] / 'datasets/kaggle'


def verify_record(directory, row):
    root = (directory / 'raw').resolve()
    path = (root / row['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Image index escapes raw directory')
    actual = image_fingerprints(path)
    if any(actual[key] != row[key] for key in ('sha256', 'pixel_sha256', 'phash', 'width', 'height')):
        raise ValueError('Image differs from audited index; re-audit before cleaning')


def select_clean(rows, issues, near_pairs):
    """Quarantine whole exact-pixel groups, retain one deterministic representative."""
    reasons = defaultdict(set)
    lookup = {row['path']: row for row in rows}
    if len(lookup) != len(rows):
        raise ValueError('Repeated image path in index')
    for path, values in issues.items():
        reasons[lookup[path]['pixel_sha256']].update(values)
    for pair in near_pairs:
        for path in (pair['left'], pair['right']):
            reasons[lookup[path]['pixel_sha256']].add('near_duplicate_requires_review')
    groups = defaultdict(list)
    for row in rows:
        groups[row['pixel_sha256']].append(row)
    accepted, quarantine, redundant = [], [], []
    for digest, group in sorted(groups.items()):
        if len({row['label'] for row in group if 'label' in row}) > 1:
            reasons[digest].add('identical_pixels_conflicting_folder_labels')
        group.sort(key=lambda row: row['path'])
        if reasons[digest]:
            quarantine.extend({'path': row['path'], 'reasons': sorted(reasons[digest])} for row in group)
        else:
            accepted.append(group[0])
            redundant.extend({'path': row['path'], 'representative': group[0]['path']} for row in group[1:])
    return accepted, quarantine, redundant


def write_view(directory, accepted, quarantine, redundant, detail):
    output = directory / 'cleaned'
    output.mkdir(exist_ok=True)
    summary = {'input_assets': len(accepted) + len(quarantine) + len(redundant),
               'retained_unique_images': len(accepted), 'quarantined_assets': len(quarantine),
               'redundant_exact_copies': len(redundant),
               'quarantine_reason_counts': dict(Counter(reason for row in quarantine for reason in row['reasons'])),
               'patient_identity_verified': False, 'training_ready': False, 'clinical_ready': False,
               'commercial_ready': False, 'raw_files_modified': False, **detail}
    manifest = {**summary, 'records': accepted, 'quarantine': quarantine, 'redundant': redundant}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


def clean_anemia(directory):
    rows = [json.loads(line) for line in (directory / 'audit/image_index.jsonl').read_text().splitlines()]
    book = openpyxl.load_workbook(directory / 'raw/Anemia_Data_Collection_Sheet.xlsx', read_only=True, data_only=True)
    try:
        iterator = book.worksheets[0].iter_rows(values_only=True)
        headers = next(iterator)
        if not {'IMAGE_ID', 'HB_LEVEL', 'REMARK'}.issubset(headers):
            raise ValueError('Unexpected clinical metadata schema')
        metadata = defaultdict(list)
        for values in iterator:
            row = dict(zip(headers, values))
            if row.get('IMAGE_ID') is not None:
                metadata[normalized_id(row['IMAGE_ID'])].append(row)
    finally:
        book.close()
    issues, hb_groups, labels = defaultdict(set), defaultdict(set), defaultdict(set)
    synonyms = {'anemic': 'Anemic', 'anaemic': 'Anemic', 'non-anemic': 'Non-anemic',
                'non-anaemic': 'Non-anemic', 'non anemic': 'Non-anemic', 'non anaemic': 'Non-anemic'}
    for row in rows:
        verify_record(directory, row)
        path, digest = row['path'], row['pixel_sha256']
        labels[digest].add(row['label'])
        candidates = metadata[normalized_id(path)]
        if len(candidates) != 1:
            issues[path].add('missing_or_ambiguous_metadata')
            continue
        source = candidates[0]
        if synonyms.get(str(source.get('REMARK', '')).strip().lower()) != row['label']:
            issues[path].add('metadata_label_conflict')
        try:
            hb = float(source['HB_LEVEL'])
            if not math.isfinite(hb) or hb <= 0:
                raise ValueError('Invalid Hb')
            hb_groups[digest].add(hb)
            row['source_hb_g_dl_unverified'] = hb
        except (TypeError, ValueError):
            issues[path].add('invalid_hb')
    for row in rows:
        if len(hb_groups[row['pixel_sha256']]) > 1:
            issues[row['path']].add('identical_pixels_conflicting_hb')
        if len(labels[row['pixel_sha256']]) > 1:
            issues[row['path']].add('identical_pixels_conflicting_label')
    near = json.loads((directory / 'audit/near_duplicates.json').read_text())
    accepted, quarantine, redundant = select_clean(rows, issues, near)
    return write_view(directory, accepted, quarantine, redundant,
                      {'retained_class_counts': dict(Counter(row['label'] for row in accepted)),
                       'split_created': False, 'next_gate': 'Verify patient mapping, labels and original rights; Hb is not corrected or averaged.'})


def clean_wounds(directory):
    root = next(path for path in (directory / 'raw').iterdir() if path.is_dir())
    index = [json.loads(line) for line in (directory / 'audit/image_index.jsonl').read_text().splitlines()]
    rows = [row for row in index if Path(row['path']).parent.name == 'imgs']
    split_lookup = defaultdict(set)
    for split in ('train', 'val', 'test'):
        for path in (root / 'split' / split).iterdir():
            if path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
                split_lookup[path.stem].add(split)
    groups, issues = defaultdict(list), defaultdict(set)
    for row in rows:
        verify_record(directory, row)
        row['provider_splits'] = sorted(split_lookup[Path(row['path']).stem])
        for split in row['provider_splits']:
            copies = [path for path in (root / 'split' / split).iterdir() if path.stem == Path(row['path']).stem]
            if len(copies) != 1 or image_fingerprints(copies[0])['pixel_sha256'] != row['pixel_sha256']:
                issues[row['path']].add('provider_copy_mismatch')
        mask = root / 'masks' / (Path(row['path']).stem + '.png')
        row['mask_path'] = mask.relative_to(directory / 'raw').as_posix() if mask.exists() else None
        groups[row['pixel_sha256']].append(row)
        if len(row['provider_splits']) != 1:
            issues[row['path']].add('missing_or_ambiguous_provider_split')
        if mask.exists():
            with Image.open(mask) as image:
                values = np.asarray(image.convert('L'))
                observed = set(np.unique(values))
                if not (observed.issubset({0, 1}) or observed.issubset({0, 255})) or not bool(np.any(values)):
                    issues[row['path']].add('invalid_binary_mask')
            fingerprint = image_fingerprints(mask)
            row['mask_pixel_sha256'] = fingerprint['pixel_sha256']
            row['mask_sha256'] = fingerprint['sha256']
            if (fingerprint['width'], fingerprint['height']) != (row['width'], row['height']):
                issues[row['path']].add('mask_dimension_mismatch')
        elif row['provider_splits'] != ['test']:
            issues[row['path']].add('missing_training_mask')
    for group in groups.values():
        splits = {split for row in group for split in row['provider_splits']}
        masks = {row['mask_pixel_sha256'] for row in group if row['mask_path']}
        for row in group:
            if len(splits) > 1:
                issues[row['path']].add('pixels_cross_provider_splits')
            if len(masks) > 1:
                issues[row['path']].add('identical_photo_conflicting_masks')
    near = find_near_duplicates(rows)
    accepted, quarantine, redundant = select_clean(rows, issues, near)
    assignments = defaultdict(set)
    for row in accepted:
        assignments[row['pixel_sha256']].update(row['provider_splits'])
    remaining = sum(len(splits) > 1 for splits in assignments.values())
    if remaining:
        raise ValueError('Clean view still leaks identical photos across provider splits')
    return write_view(directory, accepted, quarantine, redundant,
                      {'retained_provider_split_counts': dict(Counter(row['provider_splits'][0] for row in accepted)),
                       'remaining_exact_pixel_split_overlap': remaining, 'near_candidate_pairs_reviewed': len(near),
                       'next_gate': 'Verify patient grouping, segmentation labels and source license; provider test masks are unavailable.'})


if __name__ == '__main__':
    print(json.dumps({'cp_anemic': clean_anemia(ROOT / 'cp_anemic_v1'),
                      'co2wounds': clean_wounds(ROOT / 'co2wounds_v1')}, indent=2))
