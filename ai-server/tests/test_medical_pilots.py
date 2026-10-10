import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from train_medical_pilots import checked_path, exploratory_split  # noqa: E402


class ExploratoryPilotTests(unittest.TestCase):
    def rows(self):
        return [{'pixel_sha256': str(i), 'label': str(i % 2)} for i in range(100)]

    def test_duplicate_pixels_rejected(self):
        rows = self.rows()
        rows[-1]['pixel_sha256'] = rows[0]['pixel_sha256']
        with self.assertRaisesRegex(ValueError, 'duplicates'):
            exploratory_split(rows)

    def test_reproducible_stratified_disjoint_split(self):
        rows = self.rows()
        first = exploratory_split(rows)
        self.assertEqual(first, exploratory_split(rows))
        groups = [set(v) for v in first.values()]
        self.assertEqual(len(set.union(*groups)), len(rows))
        self.assertFalse(any(groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3)))
        for indices in first.values():
            self.assertEqual({rows[i]['label'] for i in indices}, {'0', '1'})
        self.assertTrue(all('patient_group' not in r for r in rows))

    def test_hash_mismatch_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sample').write_bytes(b'original')
            digest = hashlib.sha256(b'original').hexdigest()
            self.assertEqual(checked_path(root, 'sample', digest), root / 'sample')
            (root / 'sample').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed'):
                checked_path(root, 'sample', digest)
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                checked_path(root, '../outside', digest)
