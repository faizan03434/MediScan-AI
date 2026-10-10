import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from train_skin_research import validate_splits  # noqa: E402


class TrainingSplitTests(unittest.TestCase):
    def rows(self):
        return [{'split': split, 'label': label, 'patient_group': split,
                 'sha256': split + label, 'pixel_sha256': split + label}
                for split in ['train', 'val', 'test'] for label in ['A', 'B']]

    def test_patient_leakage_fails_closed(self):
        rows = self.rows()
        rows[-1]['patient_group'] = 'train'
        with self.assertRaisesRegex(ValueError, 'leakage'):
            validate_splits(rows, 'patient_group')

    def test_pixel_leakage_fails_even_with_distinct_files(self):
        rows = self.rows()
        rows[-1]['pixel_sha256'] = rows[0]['pixel_sha256']
        with self.assertRaisesRegex(ValueError, 'leakage'):
            validate_splits(rows, 'patient_group')

    def test_missing_class_or_split_rejected(self):
        with self.assertRaises(ValueError):
            validate_splits(self.rows()[:-1], 'patient_group')

    def test_complete_patient_disjoint_split_accepted(self):
        self.assertEqual(len(validate_splits(self.rows(), 'patient_group')['test']), 2)
