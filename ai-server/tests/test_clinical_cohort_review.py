import copy
import unittest
from training.clinical_cohort_review import review


class CohortReviewTests(unittest.TestCase):
    def manifest(self):
        cases = []
        for index, split in enumerate(['train', 'selection', 'calibration', 'external_test']):
            cases.append({'split': split, 'subject_id': str(index), 'decoded_pixel_sha256': str(index) * 64,
                'consent_for_this_use': True, 'source_rights_reviewed': True, 'reviewer_ids': ['R1', 'R2'],
                'adjudication': 'resolved', 'reference_standard': 'clinician reference fixture',
                'label_status': 'unknown_condition' if split == 'external_test' else 'supported_condition',
                'label': 'fixture', 'country': 'PK', 'device_group': 'phone', 'site_id': 'S1', 'lighting_group': 'daylight'})
        return {'cases': cases}

    def test_complete_metadata_never_approves_clinical_use(self):
        result = review(self.manifest())
        self.assertTrue(result['metadata_checks_passed'])
        self.assertFalse(result['clinical_approved'])

    def test_cross_split_patient_and_pixels_rejected(self):
        for key in ['subject_id', 'decoded_pixel_sha256']:
            manifest = self.manifest()
            manifest['cases'][-1][key] = manifest['cases'][0][key]
            self.assertFalse(review(manifest)['metadata_checks_passed'])

    def test_review_and_consent_cannot_be_assumed(self):
        for key, value in [('reviewer_ids', ['R1', 'R1']), ('consent_for_this_use', False), ('adjudication', 'unresolved')]:
            manifest = copy.deepcopy(self.manifest())
            manifest['cases'][0][key] = value
            self.assertFalse(review(manifest)['metadata_checks_passed'])

    def test_missing_external_unknowns_and_empty_template_fail(self):
        manifest = self.manifest()
        manifest['cases'][-1]['label_status'] = 'supported_condition'
        self.assertFalse(review(manifest)['metadata_checks_passed'])
        self.assertFalse(review({'cases': []})['metadata_checks_passed'])
