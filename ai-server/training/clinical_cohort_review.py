"""Check cohort review metadata and separation; never authenticate clinical claims."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def review(manifest):
    reasons, subjects, pixels, counts = set(), {}, {}, Counter()
    cases = manifest.get('cases', [])
    if not cases:
        reasons.add('no_reviewed_cases')
    for case in cases:
        split, subject = case.get('split'), case.get('subject_id')
        if split not in {'train', 'selection', 'calibration', 'external_test'} or not isinstance(subject, str) or not subject.strip():
            reasons.add('valid_subject_and_split_required')
            continue
        counts[split] += 1
        if subject in subjects and subjects[subject] != split:
            reasons.add('subject_cross_split_leakage')
        subjects[subject] = split
        digest = case.get('decoded_pixel_sha256', '')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            reasons.add('audited_decoded_pixel_sha256_required')
        elif digest in pixels and pixels[digest] != split:
            reasons.add('decoded_pixel_cross_split_leakage')
        else:
            pixels[digest] = split
        if case.get('consent_for_this_use') is not True or case.get('source_rights_reviewed') is not True:
            reasons.add('consent_and_source_rights_review_required')
        reviewers = case.get('reviewer_ids', [])
        if not isinstance(reviewers, list) or len({r for r in reviewers if isinstance(r, str) and r.strip()}) < 2:
            reasons.add('two_independent_clinician_review_records_required')
        if case.get('adjudication') != 'resolved' or not case.get('reference_standard'):
            reasons.add('resolved_labels_and_reference_standard_required')
        if case.get('label_status') not in {'supported_condition', 'unknown_condition'} or not case.get('label'):
            reasons.add('explicit_supported_or_unknown_ground_truth_required')
        if split == 'external_test' and case.get('country') != 'PK':
            reasons.add('pakistan_external_cohort_required')
        if not case.get('device_group') or not case.get('site_id') or not case.get('lighting_group'):
            reasons.add('device_site_and_lighting_metadata_required')
    if not counts['calibration'] or not counts['external_test']:
        reasons.add('separate_calibration_and_external_test_required')
    if not any(c.get('split') == 'external_test' and c.get('label_status') == 'unknown_condition' for c in cases):
        reasons.add('external_unknown_condition_examples_required')
    return {'metadata_checks_passed': not reasons, 'unmet_requirements': sorted(reasons),
        'case_counts': dict(counts), 'distinct_subjects': len(subjects), 'clinical_approved': False,
        'limitation': 'Metadata assertions are not authenticated clinical evidence. Independent consent, clinician credentials, diagnosis, cohort adequacy and near-duplicate review remain required.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    result = review(json.loads(raw))
    result['manifest_sha256'] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(result, indent=2))
