import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from audit_missing_labels import annotation_geometry, nail_identity, source_class_map  # noqa: E402
from clinical_label_contracts import evidence, validate_reference_manifest  # noqa: E402
from compare_original_nails import validate_members  # noqa: E402


class LabelGapTests(unittest.TestCase):
    def test_original_archive_layout_rejects_traversal_and_nonimage_payloads(self):
        validate_members(['Fingernails/', 'Fingernails/Anemic-FN-1 (2).png'])
        for invalid in ('../outside.png', '/outside.png', 'C:/outside.png', 'Fingernails/../outside.png', 'Fingernails/run.exe'):
            with self.assertRaises(ValueError):
                validate_members([invalid])
    def test_explicit_source_class_map_is_recovered_without_inventing_diagnoses(self):
        payload = b"nc: 6\nnames: ['abu abu', 'hitam', 'kuning', 'normal', 'putih', 'ungu']\n"
        labels = source_class_map(payload)
        self.assertEqual(labels[3], 'normal')
        self.assertNotIn('anemia', labels)
        self.assertNotIn('healthy', labels)
        with self.assertRaises(ValueError):
            source_class_map(b"nc: 3\nnames: ['white', 'yellow']\n")
    def test_filename_labels_are_not_confused_and_augmentations_share_a_family(self):
        label, family, issue = nail_identity('Fingernails/Anemic-Fin-007 (10).png')
        self.assertEqual(label, 'Anemic')
        self.assertEqual(family, nail_identity('Anemic-FN-7.png')[1])
        self.assertIsNone(issue)
        self.assertEqual(nail_identity('Non-anemic-Fin-7.png')[0], 'Non-anemic')
        self.assertNotEqual(family, nail_identity('Non-anemic-Fin-7.png')[1])
        self.assertIsNone(nail_identity('Non-Anrmic-FN-7.png')[0])
        self.assertEqual(nail_identity('Non-Anrmic-FN-7.png')[2], 'unconfirmed_provider_spelling')
        self.assertIsNone(nail_identity('unlabelled-image.png')[0])

    def test_mixed_annotation_geometry_is_explicit_and_invalid_coordinates_fail(self):
        self.assertEqual(annotation_geometry('2 .5 .5 .4 .4'), (2, 'box'))
        self.assertEqual(annotation_geometry('1 0 0 1 0 1 1 0 1'), (1, 'polygon'))
        for invalid in ('1 nan 0 1 1', '-1 .5 .5 .2 .2', '1 .1 .1 .8 .8', '1 0 0 .5 .5 1 1', '1 0 0 1'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                annotation_geometry(invalid)

    def fixture(self, root):
        payload = b'synthetic test fixture; not a real clinical approval'
        (root / 'fixture.txt').write_bytes(payload)
        proof = {'path': 'fixture.txt', 'sha256': hashlib.sha256(payload).hexdigest()}
        row = {'subject_pseudonym': 'a' * 64, 'image_sha256': 'b' * 64, 'split': 'train',
            'modality': 'tongue_external_photo', 'review_status': 'adjudicated',
            'reviewer_id': 'reviewer-a', 'second_reviewer_id': 'reviewer-b',
            'reference_evidence': proof, 'attributes': {'cracks': True}}
        return {'task': 'tongue_appearance', 'intended_use': 'research',
            'rights': {'status': 'declared_open_license_reviewed', 'permitted_uses': ['research'], 'evidence': proof},
            'annotation_protocol': proof, 'data_use_basis': 'licensed_research_dataset',
            'privacy_review': proof, 'records': [row]}

    def test_valid_structure_does_not_certify_identity_or_approve_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = validate_reference_manifest(self.fixture(root), root)
            self.assertEqual(result['records_structurally_valid'], 1)
            self.assertFalse(result['clinical_approved'])
            self.assertFalse(result['deployment_authorized'])

    def test_pending_permission_and_uncovered_commercial_use_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            manifest['rights']['status'] = 'request_submitted'
            with self.assertRaisesRegex(ValueError, 'not a grant'):
                validate_reference_manifest(manifest, root)
            manifest = self.fixture(root)
            manifest['intended_use'] = 'commercial_development'
            with self.assertRaisesRegex(ValueError, 'not covered'):
                validate_reference_manifest(manifest, root)

    def test_subject_split_leakage_and_identical_reviewer_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            second = copy.deepcopy(manifest['records'][0])
            second.update(split='external_test', image_sha256='c' * 64, subject_pseudonym='A' * 64)
            manifest['records'].append(second)
            with self.assertRaisesRegex(ValueError, 'Subject split leakage'):
                validate_reference_manifest(manifest, root)
            manifest = self.fixture(root)
            manifest['records'][0]['second_reviewer_id'] = 'reviewer-a'
            with self.assertRaisesRegex(ValueError, 'distinct reviewer'):
                validate_reference_manifest(manifest, root)

    def test_appearance_attributes_cannot_become_organ_or_disease_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            manifest['records'][0]['attributes'] = {'kidney_disease': True}
            with self.assertRaisesRegex(ValueError, 'appearance attributes'):
                validate_reference_manifest(manifest, root)
            manifest = self.fixture(root)
            manifest['records'][0]['disease_label'] = 'anemia'
            with self.assertRaisesRegex(ValueError, 'disease confirmation'):
                validate_reference_manifest(manifest, root)
            manifest = self.fixture(root)
            manifest['records'][0]['clinical_label'] = 'anemia'
            with self.assertRaisesRegex(ValueError, 'disease confirmation'):
                validate_reference_manifest(manifest, root)

    def test_nail_reference_requires_hb_units_timing_and_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            manifest['task'] = 'fingernail_anemia'
            row = manifest['records'][0]
            row.update(modality='fingernail_photo', reference_kind='laboratory_hb_report', hb_g_dl=10.,
                hb_unit='g/dL', clinical_label='indeterminate', age_months=24,
                captured_at='2026-10-01T10:00:00+05:00', reference_at='2026-10-01T09:00:00+05:00',
                timing_reviewed_under_protocol=True)
            self.assertEqual(validate_reference_manifest(manifest, root)['records_structurally_valid'], 1)
            row['hb_unit'] = 'unknown'
            with self.assertRaisesRegex(ValueError, 'unit-labelled'):
                validate_reference_manifest(manifest, root)

    def test_scoliosis_does_not_substitute_xray_for_camera_or_screening_for_diagnosis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            manifest['task'] = 'scoliosis_phone_screening'
            row = manifest['records'][0]
            row.update(modality='spine_radiograph', reference_kind='clinician_screening', clinical_label='screen_positive')
            with self.assertRaisesRegex(ValueError, 'Modality'):
                validate_reference_manifest(manifest, root)
            row.update(modality='back_photo', clinical_label='confirmed_scoliosis')
            with self.assertRaisesRegex(ValueError, 'must not be renamed'):
                validate_reference_manifest(manifest, root)

    def test_reference_file_tampering_and_external_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            (root / 'fixture.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                validate_reference_manifest(manifest, root)
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                evidence(root, {'path': '../outside', 'sha256': 'a' * 64})
