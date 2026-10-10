import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from routers.model_status import research_skin_status


class ModelReadinessTests(unittest.TestCase):
    def test_research_metadata_cannot_enable_clinical_or_commercial_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / 'weights.pt'
            checkpoint.write_bytes(b'research fixture')
            card = {'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                    'classes': ['Eczema'], 'split_counts': {'train': 10, 'val': 3, 'test': 3},
                    'test_balanced_accuracy': .99, 'limitations': ['Not validated'],
                    'clinical_approved': True}
            (root / 'model_card.json').write_text(json.dumps(card))
            result = research_skin_status(root)
            self.assertEqual(result['status'], 'trained_unvalidated')
            self.assertFalse(result['clinical_approved'])
            self.assertFalse(result['commercial_release_allowed'])
            checkpoint.write_bytes(b'changed')
            self.assertEqual(research_skin_status(root)['status'], 'integrity_failed')

    def test_partial_training_checkpoint_is_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'weights.pt').write_bytes(b'incomplete')
            self.assertEqual(research_skin_status(root)['status'], 'not_trained')

    def test_segmentation_card_reports_dice_without_classification_accuracy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'weights.pt').write_bytes(b'segmentation fixture')
            card = {'checkpoint_sha256': hashlib.sha256(b'segmentation fixture').hexdigest(),
                    'test_evaluated': False, 'test_balanced_accuracy': .99,
                    'validation_dice': .4, 'validation_iou': .3,
                    'split_counts': {'train': 12, 'val': 4}, 'limitations': ['No test masks']}
            (root / 'model_card.json').write_text(json.dumps(card))
            result = research_skin_status(root)
            self.assertEqual(result['status'], 'trained_validation_only')
            self.assertEqual(result['validation_dice'], .4)
            self.assertIsNone(result['test_balanced_accuracy'])
            self.assertFalse(result['clinical_approved'])

    def test_validation_selected_model_never_reports_a_test_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'weights.pt').write_bytes(b'validation model')
            card = {'checkpoint_sha256': hashlib.sha256(b'validation model').hexdigest(),
                    'classes': ['Eczema'], 'split_counts': {'train': 10, 'val': 3, 'test': 3},
                    'validation_balanced_accuracy': .99, 'test_evaluated': False,
                    'commercial_release_allowed': True, 'limitations': ['Validation selected']}
            (root / 'model_card.json').write_text(json.dumps(card))
            result = research_skin_status(root)
            self.assertEqual(result['status'], 'trained_validation_only')
            self.assertIsNone(result['test_balanced_accuracy'])
            self.assertFalse(result['test_evaluated'])
            self.assertFalse(result['commercial_release_allowed'])
