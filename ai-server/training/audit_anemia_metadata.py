"""Aggregate-only QC of image/Hb metadata; image IDs are never inferred to be patients."""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1] / 'datasets/kaggle/cp_anemic_v1'


def normalized_id(value):
    return Path(str(value).strip().replace('\\', '/')).stem.lower()


def check(root=ROOT):
    book = openpyxl.load_workbook(root / 'raw/Anemia_Data_Collection_Sheet.xlsx', read_only=True, data_only=True)
    try:
        sheet = book.worksheets[0]
        iterator = sheet.iter_rows(values_only=True)
        headers = list(next(iterator))
        if not {'IMAGE_ID', 'HB_LEVEL', 'REMARK'}.issubset(headers):
            raise ValueError('Unexpected source metadata schema')
        metadata = [dict(zip(headers, values)) for values in iterator if any(value is not None for value in values)]
    finally:
        book.close()
    mapping = defaultdict(list)
    for row in metadata:
        if row.get('IMAGE_ID') is not None:
            mapping[normalized_id(row['IMAGE_ID'])].append(row)
    index = [json.loads(line) for line in (root / 'audit/image_index.jsonl').read_text().splitlines() if line]
    matched, ambiguous, absent, unknown_remark, conflicting_label, invalid_hb = 0, 0, 0, 0, 0, 0
    synonyms = {'anemic': 'Anemic', 'anaemic': 'Anemic', 'non-anemic': 'Non-anemic',
                'non-anaemic': 'Non-anemic', 'non anemic': 'Non-anemic', 'non anaemic': 'Non-anemic'}
    pixel_hb = defaultdict(set)
    for image in index:
        candidates = mapping.get(normalized_id(image['path']), [])
        if not candidates:
            absent += 1
            continue
        if len(candidates) != 1:
            ambiguous += 1
            continue
        matched += 1
        row = candidates[0]
        remark = synonyms.get(str(row.get('REMARK', '')).strip().lower())
        unknown_remark += remark is None
        conflicting_label += remark is not None and remark != image['label']
        try:
            hb = float(row['HB_LEVEL'])
            if not math.isfinite(hb) or hb <= 0:
                raise ValueError('Invalid Hb')
            pixel_hb[image['pixel_sha256']].add(hb)
        except (TypeError, ValueError):
            invalid_hb += 1
    report = {'metadata_rows': len(metadata), 'columns': headers, 'unique_image_identifiers': len(mapping),
              'images_matched_to_single_metadata_row': matched, 'images_missing_metadata': absent,
              'images_with_ambiguous_metadata': ambiguous, 'unrecognized_metadata_remarks': unknown_remark,
              'folder_metadata_label_conflicts': conflicting_label, 'matched_images_invalid_or_missing_hb': invalid_hb,
              'identical_pixel_groups_with_different_hb': sum(len(values) > 1 for values in pixel_hb.values()),
              'image_id_value_types': dict(Counter(type(row['IMAGE_ID']).__name__ for row in metadata)),
              'patient_mapping_verified': False, 'training_ready': False, 'clinical_ready': False,
              'limitations': ['IMAGE_ID is not a verified independent patient identifier',
                  'Original and mirror provenance/duplicate/label conflicts require review',
                  'Pediatric Ghana data does not validate adult Pakistan screening',
                  'No Hb-based diagnosis or threshold is assigned by this QC tool']}
    (root / 'audit/metadata_qc.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
