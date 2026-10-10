"""Audit original sitting labels, preserve subject separation; no scoliosis labels."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from acquire_tongue_posture_open import file_digest

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'datasets/original/sitting_posture_zenodo_14230872'
UPPER = {'TUP', 'TLB', 'TLF', 'TLR', 'TLL'}
LOWER = {'LAP', 'LWA', 'LCS', 'LCR', 'LCL', 'LLR', 'LLL'}


def subject_split(subjects):
    """Deterministic hash-order 60/20/remainder split of subjects, never frames."""
    subjects = sorted(set(subjects), key=lambda s: hashlib.sha256(('mediscan42:' + s).encode()).hexdigest())
    if len(subjects) < 5:
        raise ValueError('Too few independent subjects')
    train, val = max(1, int(.6 * len(subjects))), max(1, int(.2 * len(subjects)))
    return {'train': subjects[:train], 'val': subjects[train:train + val], 'test': subjects[train + val:]}


def main():
    path = DIRECTORY / 'data.csv'
    if file_digest(path, 'md5') != '7efbc94d653acf32eefecec3ff26d6c6':
        raise ValueError('Source integrity failed')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        features = [c for c in reader.fieldnames if c.endswith(('_x', '_y', '_z'))]
        rows = list(reader)
    if len(features) != 99 or not rows:
        raise ValueError('Unexpected actual coordinate schema')
    for row in rows:
        if not row['subject'] or row['upperbody_label'] not in UPPER or row['lowerbody_label'] not in LOWER:
            raise ValueError('Missing subject or unsupported label')
        if not all(math.isfinite(float(row[c])) for c in features):
            raise ValueError('Invalid coordinate')
    groups = subject_split([r['subject'] for r in rows])
    manifest = {'source_sha256': file_digest(path, 'sha256'), 'features': features, 'subject_splits': groups,
        'clinical_ready': False, 'scope': 'sitting posture recognition; not scoliosis',
        'patient_identity_verified': False, 'subject_identifier_source': 'provider subject column',
        'clinical_ground_truth_reviewed': False}
    report = {'rows': len(rows), 'subjects': len(set(r['subject'] for r in rows)),
        'actual_feature_count': len(features), 'declared_paper_feature_count': 33,
        'schema_difference': 'Actual CSV exposes 33 joints x3; do not assume the paper subset.',
        'license': 'CC BY 4.0', 'clinical_ready': False, 'scoliosis_labels_available': False, 'splits': {}}
    fingerprints = {}
    for split, subjects in groups.items():
        selected = [r for r in rows if r['subject'] in subjects]
        report['splits'][split] = {'subjects': len(subjects), 'rows': len(selected),
            'upper_labels': dict(Counter(r['upperbody_label'] for r in selected)),
            'lower_labels': dict(Counter(r['lowerbody_label'] for r in selected))}
        for r in selected:
            fingerprint = tuple(float(r[c]) for c in features)
            if fingerprint in fingerprints and fingerprints[fingerprint] != split:
                raise ValueError('Exact coordinate overlap across subject splits')
            fingerprints[fingerprint] = split
    (DIRECTORY / 'subject_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (ROOT.parent / 'docs/SITTING_POSTURE_INTAKE.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
