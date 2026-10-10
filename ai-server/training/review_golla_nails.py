"""Keep new nail pixels separate from unverified source labels and existing mirrors."""
import json
from collections import Counter
from pathlib import Path

from training.clean_medical_intake import select_clean

ROOT = Path(__file__).resolve().parents[1] / 'datasets'


def review():
    directory = ROOT / 'kaggle/golla_fingernail_detection_v1'
    rows = [json.loads(line) for line in (directory / 'audit/image_index.jsonl').read_text().splitlines() if line]
    sources = {'ghana_nails': ROOT / 'kaggle/ghana_fingernails_v1/audit/image_index.jsonl',
               'cp_anemic': ROOT / 'kaggle/cp_anemic_v1/audit/image_index.jsonl'}
    hashes = {name: {json.loads(line)['pixel_sha256'] for line in path.read_text().splitlines() if line}
              for name, path in sources.items()}
    existing = set().union(*hashes.values())
    issues = {row['path']: {'already_present_in_existing_source'} for row in rows if row['pixel_sha256'] in existing}
    near = json.loads((directory / 'audit/near_duplicates.json').read_text())
    accepted, quarantine, redundant = select_clean(rows, issues, near)
    summary = {'input_assets': len(rows), 'new_unique_candidate_pixels': len(accepted),
               'candidate_folder_counts': dict(Counter(row['label'] for row in accepted)),
               'quarantined_assets': len(quarantine), 'redundant_consistent_copies': len(redundant),
               'exact_pixel_overlap_unique_counts': {name: len({row['pixel_sha256'] for row in rows} & values)
                                                      for name, values in hashes.items()},
               'quarantine_reason_counts': dict(Counter(reason for row in quarantine for reason in row['reasons'])),
               'raw_files_modified': False, 'training_ready': False, 'clinical_ready': False,
               'commercial_ready': False, 'patient_identity_verified': False,
               'limitations': ['Unknown original license/source.', 'No lab Hb/patient mapping or original/augmentation lineage.',
                               'Anemic/NonAnemic are mirror folder labels, not verified clinical labels.',
                               'Exact pixel comparison does not rule out transformed cross-source copies.']}
    (directory / 'research_candidate_manifest.json').write_text(json.dumps({**summary, 'records': accepted,
                                                                         'quarantine': quarantine, 'redundant': redundant}, indent=2))
    (directory / 'review_summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    review()
