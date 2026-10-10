import json
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from audit_anemia_metadata import check  # noqa: E402


class AnemiaMetadataTests(unittest.TestCase):
    def fixture(self, root, metadata, images):
        (root / 'raw').mkdir()
        (root / 'audit').mkdir()
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.append(['IMAGE_ID', 'HB_LEVEL', 'REMARK'])
        for row in metadata:
            sheet.append(row)
        book.save(root / 'raw/Anemia_Data_Collection_Sheet.xlsx')
        book.close()
        (root / 'audit/image_index.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in images))

    def test_duplicate_pixels_with_conflicting_hb_and_labels_are_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [('A', 8, 'Anemic'), ('B', 12, 'Anemic')], [
                {'path': 'Anemic/A.png', 'label': 'Anemic', 'pixel_sha256': 'same'},
                {'path': 'Non-anemic/B.png', 'label': 'Non-anemic', 'pixel_sha256': 'same'}])
            result = check(root)
            self.assertEqual(result['identical_pixel_groups_with_different_hb'], 1)
            self.assertEqual(result['folder_metadata_label_conflicts'], 1)
            self.assertFalse(result['training_ready'])
            self.assertFalse(result['patient_mapping_verified'])

    def test_ambiguous_image_identifier_is_not_treated_as_patient_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [('A', 8, 'Anemic'), ('A', 12, 'Non-anemic')], [
                {'path': 'Anemic/A.png', 'label': 'Anemic', 'pixel_sha256': 'image'}])
            result = check(root)
            self.assertEqual(result['images_with_ambiguous_metadata'], 1)
            self.assertEqual(result['images_matched_to_single_metadata_row'], 0)
            self.assertFalse(result['clinical_ready'])
