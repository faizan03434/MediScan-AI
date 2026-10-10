import sys
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from acquire_skin_kaggle import safe_extract  # noqa: E402 — import CLI helpers from the scoped training directory
from skin_data_audit import audit, find_near_duplicates  # noqa: E402
from build_patient_skin_split import build_split  # noqa: E402
from audit_skin_overlap import compare  # noqa: E402

class SkinIntakeTests(unittest.TestCase):
    def test_cross_source_duplicates_detected_without_merging_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {}
            for source, label in [('one', 'Eczema'), ('two', 'Different taxonomy')]:
                paths[source] = root / (source + '.jsonl')
                paths[source].write_text(json.dumps({'path': 'same.png', 'label': label,
                    'pixel_sha256': 'same', 'phash': '000000000000001f'}) + '\n')
            result = compare(paths)
            self.assertEqual(result['unique_decoded_images_across_sources'], 1)
            self.assertEqual(result['cross_source_exact_groups'], 1)
            self.assertFalse(result['labels_merged'])
    def test_unsafe_archive_path_rejected_before_any_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'source.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('safe.jpg', b'fixture')
                output.writestr('../outside.csv', b'fixture')
            with self.assertRaises(ValueError):
                safe_extract(archive, root / 'raw')
            self.assertFalse((root / 'raw/safe.jpg').exists())
    def test_exact_pixel_duplicates_and_augmented_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label in ['Eczema', 'Tinea', 'Augmented/Eczema']:
                (root / 'raw' / label).mkdir(parents=True)
            image = Image.new('RGB', (48, 48), 'white')
            ImageDraw.Draw(image).rectangle((4, 7, 30, 35), fill='red')
            image.save(root / 'raw/Eczema/a.png')
            image.save(root / 'raw/Tinea/copy.png')
            image.save(root / 'raw/Augmented/Eczema/rotated.png')
            (root / 'raw/Eczema/bad.jpg').write_bytes(b'broken')
            report = audit(root / 'raw', root / 'audit')
            self.assertEqual(report['images_decoded'], 2)
            self.assertEqual(report['unique_decoded_images'], 1)
            self.assertEqual(report['exact_duplicate_groups'], 1)
            self.assertEqual(report['excluded_augmented_images'], 1)
            self.assertEqual(report['rejected_images'], 1)
            self.assertFalse(report['training_ready'])
            self.assertFalse(report['patient_mapping_verified'])
    def test_windows_archive_paths_normalized_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'windows.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('Processed\\Eczema\\sample.jpg', b'fixture')
            safe_extract(archive, root / 'raw')
            self.assertEqual((root / 'raw/Processed/Eczema/sample.jpg').read_bytes(), b'fixture')
            with zipfile.ZipFile(root / 'traversal.zip', 'w') as output:
                output.writestr('folder\\..\\..\\escape.csv', b'fixture')
            with self.assertRaises(ValueError):
                safe_extract(root / 'traversal.zip', root / 'raw')
    def test_near_duplicate_conflicting_labels_flagged(self):
        rows = [{'path': 'a', 'phash': '000000000000001f', 'pixel_sha256': 'a', 'label': 'Acne'},
                {'path': 'b', 'phash': '000000000000001e', 'pixel_sha256': 'b', 'label': 'Eczema'}]
        pair = find_near_duplicates(rows)[0]
        self.assertEqual(pair['hamming_distance'], 1)
        self.assertTrue(pair['label_conflict'])
    def test_missing_patient_metadata_cannot_make_image_split(self):
        with self.assertRaises(ValueError):
            build_split([{'path': 'a.jpg', 'label': 'Eczema', 'pixel_sha256': 'a'}], [], 'image', 'patient', 'fixture')
    def test_patient_and_duplicate_groups_cannot_cross_splits(self):
        index, metadata = [], []
        for patient in range(20):
            for label in ['Acne', 'Eczema']:
                path = f'patient{patient}/{label}.jpg'
                fingerprint = f'{patient}-{label}'
                if patient == 1 and label == 'Acne':
                    fingerprint = '0-Acne'
                index.append({'path': path, 'label': label, 'pixel_sha256': fingerprint})
                metadata.append({'image': path, 'patient': str(patient)})
        manifest = build_split(index, metadata, 'image', 'patient', 'fixture')
        for key in ['patient_group', 'pixel_sha256']:
            memberships = {}
            for row in manifest['records']:
                memberships.setdefault(row[key], set()).add(row['split'])
            self.assertTrue(all(len(splits) == 1 for splits in memberships.values()))
        self.assertFalse(manifest['clinical_ready'])
        self.assertFalse(manifest['patient_identity_semantics_verified'])

if __name__ == '__main__':
    unittest.main()
