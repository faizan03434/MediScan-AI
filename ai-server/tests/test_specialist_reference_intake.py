import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from clinical_label_contracts import DIAGNOSTIC_REFERENCES, TASKS, validate_reference_manifest  # noqa: E402


class SpecialistReferenceTests(unittest.TestCase):
    def fixture(self, root, task):
        def proof(name):
            return {'path': name, 'sha256': hashlib.sha256((root / name).read_bytes()).hexdigest()}
        (root / 'synthetic.txt').write_text('Synthetic fixture, not a real clinical reference')
        Image.new('RGB', (10, 8), 'white').save(root / 'photo.png')
        Image.new('L', (10, 8), 255).save(root / 'mask.png')
        source = proof('photo.png')
        reference = proof('synthetic.txt')
        row = {'subject_pseudonym': 'a' * 64, 'image_sha256': source['sha256'], 'image_evidence': source,
            'split': 'external_test', 'modality': TASKS[task], 'review_status': 'adjudicated',
            'reviewer_id': 'specialist-a', 'second_reviewer_id': 'specialist-b',
            'reference_evidence': reference, 'reference_kind': DIAGNOSTIC_REFERENCES.get(task, 'clinician_wound_annotation'),
            'clinical_label': 'indeterminate', 'label_status': 'indeterminate', 'reference_method': 'clinical_examination',
            'mask_evidence': proof('mask.png'), 'wound_present': True, 'measurement_claimed': False}
        return {'task': task, 'intended_use': 'research', 'data_use_basis': 'licensed_research_dataset',
            'rights': {'status': 'declared_open_license_reviewed', 'permitted_uses': ['research'], 'evidence': reference},
            'annotation_protocol': reference, 'privacy_review': reference, 'records': [row]}

    def test_specialist_tasks_accept_only_structure_never_authorize_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for task in DIAGNOSTIC_REFERENCES:
                with self.subTest(task=task):
                    result = validate_reference_manifest(self.fixture(root, task), root)
                    self.assertEqual(result['records_structurally_valid'], 1)
                    self.assertFalse(result['clinical_approved'])
                    self.assertFalse(result['deployment_authorized'])

    def test_retina_cannot_be_substituted_for_external_eye(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root, 'external_eye_disease')
            manifest['records'][0]['modality'] = 'fundus_photo'
            with self.assertRaisesRegex(ValueError, 'Modality'):
                validate_reference_manifest(manifest, root)
            manifest['records'][0].update(modality='external_eye_photo', reference_method='fundus_examination')
            with self.assertRaisesRegex(ValueError, 'Fundus reference'):
                validate_reference_manifest(manifest, root)

    def test_wrong_specialist_folder_labels_and_changed_image_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = self.fixture(root, 'skin_disease')
            for field, value in [('reference_kind', 'folder_name'), ('reference_method', 'kaggle_directory'),
                                 ('label_status', 'unreviewed'), ('clinical_label', '  '), ('image_sha256', 'c' * 64)]:
                manifest = copy.deepcopy(original)
                manifest['records'][0][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    validate_reference_manifest(manifest, root)
            (root / 'photo.png').write_bytes(b'changed image')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                validate_reference_manifest(original, root)

    def test_wound_mask_valid_but_not_size_or_healing_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root, 'wound_segmentation')
            self.assertEqual(validate_reference_manifest(manifest, root)['records_structurally_valid'], 1)
            manifest['records'][0]['measurement_claimed'] = True
            with self.assertRaisesRegex(ValueError, 'longitudinal protocol'):
                validate_reference_manifest(manifest, root)

    def test_wound_masks_must_match_geometry_presence_and_binary_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for size, value, present in [((9, 8), 255, True), ((10, 8), 123, True), ((10, 8), 0, True), ((10, 8), 255, False)]:
                manifest = self.fixture(root, 'wound_segmentation')
                Image.new('L', size, value).save(root / 'mask.png')
                manifest['records'][0]['mask_evidence']['sha256'] = hashlib.sha256((root / 'mask.png').read_bytes()).hexdigest()
                manifest['records'][0]['wound_present'] = present
                with self.subTest(size=size, value=value, present=present), self.assertRaises(ValueError):
                    validate_reference_manifest(manifest, root)


if __name__ == '__main__':
    unittest.main()
