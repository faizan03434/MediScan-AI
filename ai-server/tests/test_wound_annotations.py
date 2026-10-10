import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from training.audit_wound_annotations import check


class WoundAnnotationTests(unittest.TestCase):
    def test_binary_one_masks_and_provider_pixel_leakage_are_recognized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('imgs', 'masks', 'split/train', 'split/val', 'split/test', 'annotations'):
                (root / folder).mkdir(parents=True)
            for key, split in (('a', 'train'), ('b', 'val')):
                image = Image.new('RGB', (3, 3), 'red')
                image.save(root / 'imgs' / (key + '.png'))
                image.save(root / 'split' / split / (key + '.png'))
                Image.new('L', (3, 3), 1).save(root / 'masks' / (key + '.png'))
            (root / 'annotations/annotations.json').write_text(json.dumps({
                'images': [{'id': 1, 'file_name': 'a.png'}, {'id': 2, 'file_name': 'b.png'}],
                'annotations': [{'image_id': 1}],
            }))
            result = check(root)
            self.assertEqual(result['non_binary_masks'], 0)
            self.assertEqual(result['mask_dimension_mismatches'], 0)
            self.assertEqual(result['pixel_groups_crossing_provider_splits'], 1)
            self.assertFalse(result['training_ready'])
            Image.new('L', (2, 2), 42).save(root / 'masks/b.png')
            result = check(root)
            self.assertEqual(result['non_binary_masks'], 1)
            self.assertEqual(result['mask_dimension_mismatches'], 1)


if __name__ == '__main__':
    unittest.main()
