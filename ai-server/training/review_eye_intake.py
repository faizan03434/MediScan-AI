"""Keep eye mirrors separate; duplicate checking does not validate clinical labels."""
import json
import csv
from collections import Counter, defaultdict
from pathlib import Path

from training.clean_medical_intake import select_clean
from training.skin_data_audit import find_near_duplicates

ROOT = Path(__file__).resolve().parents[1] / 'datasets'
SOURCES = ('eye_conjunctivitis_alisofiya', 'eye_conjunctivitis_revengerdna')


def review():
    summary, combined = {}, []
    for name in SOURCES:
        directory = ROOT / 'kaggle' / (name + '_v1')
        rows = [json.loads(line) for line in (directory / 'audit/image_index.jsonl').read_text().splitlines() if line]
        accepted, quarantine, redundant = select_clean(
            rows, {}, json.loads((directory / 'audit/near_duplicates.json').read_text()))
        report = {'input_image_assets': len(rows), 'retained_unique_candidates': len(accepted),
                  'candidate_folder_counts': dict(Counter(row['label'] for row in accepted)),
                  'quarantined_assets': len(quarantine), 'redundant_consistent_copies': len(redundant),
                  'labels_are_unverified_folder_names': True, 'patient_identity_verified': False,
                  'training_ready': False, 'clinical_ready': False, 'commercial_ready': False}
        (directory / 'research_candidate_manifest.json').write_text(json.dumps({**report, 'records': accepted,
                                                                              'quarantine': quarantine, 'redundant': redundant}, indent=2))
        template = directory / 'annotation_review.csv'
        if not template.exists():
            with template.open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=['image_path', 'pixel_sha256', 'source_folder_label',
                                                            'reviewed_body_area', 'reviewed_diagnosis',
                                                            'pseudonymous_patient_group', 'quality_status',
                                                            'reviewer_reference', 'reviewed_at', 'review_status'])
                writer.writeheader()
                for row in accepted:
                    writer.writerow({'image_path': row['path'], 'pixel_sha256': row['pixel_sha256'],
                                     'source_folder_label': row['label'], 'review_status': 'pending'})
        summary[name] = report
        combined.extend({**row, 'path': name + ':' + row['path'], 'source': name} for row in rows)
    groups = defaultdict(list)
    for row in combined:
        groups[row['pixel_sha256']].append(row)
    cross_exact = [group for group in groups.values() if len({row['source'] for row in group}) > 1]
    unique_by_source = {}
    for row in combined:
        unique_by_source[(row['source'], row['pixel_sha256'])] = row
    near = [pair for pair in find_near_duplicates(list(unique_by_source.values()))
            if pair['left'].split(':', 1)[0] != pair['right'].split(':', 1)[0]]
    report = {'sources': summary, 'combined_asset_count': len(combined),
              'unique_pixels_across_mirrors': len(groups), 'cross_source_exact_pixel_groups': len(cross_exact),
              'cross_source_near_candidate_pairs': len(near), 'clinical_labels_merged': False,
              'training_ready': False, 'clinical_ready': False,
              'limitations': ['Folder labels are not clinically verified.', 'No verified patient/site separation.',
                              'Original image rights and capture modality require review.',
                              'Both classes and other red-eye causes are needed for a screening task.']}
    output = ROOT / 'catalog/eye_links'
    (output / 'conjunctivitis_cross_source_review.json').write_text(json.dumps({**report, 'near_candidates': near}, indent=2))
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    review()
