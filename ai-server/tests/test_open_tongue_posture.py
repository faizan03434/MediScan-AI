import sys
import unittest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from acquire_tongue_posture_open import download_csv, verify_metadata  # noqa: E402
from prepare_sitting_posture import subject_split  # noqa: E402


class OpenSourceTests(unittest.TestCase):
    def metadata(self):
        return {'id': 14230872, 'metadata': {'access_right': 'open', 'license': {'id': 'cc-by-4.0'}},
                'files': [{'key': 'data.csv', 'size': 20, 'checksum': 'md5:abc'}]}

    def test_pinned_file_required(self):
        self.assertEqual(verify_metadata(self.metadata(), 14230872, 'data.csv', 20, 'abc')['size'], 20)
        with self.assertRaises(ValueError):
            verify_metadata(self.metadata(), 14230872, 'data.csv', 21, 'abc')

    def test_access_and_license_change_rejected(self):
        for field, value in [('access_right', 'restricted'), ('license', {'id': 'cc-by-nc-4.0'})]:
            metadata = self.metadata()
            metadata['metadata'][field] = value
            with self.assertRaises(ValueError):
                verify_metadata(metadata, 14230872, 'data.csv', 20, 'abc')

    def test_mirror_identity_cannot_replace_original_record(self):
        with self.assertRaises(ValueError):
            verify_metadata(self.metadata(), 123, 'data.csv', 20, 'abc')

    def test_related_frames_never_split_subjects(self):
        subjects = [str(i) for i in range(13)]
        split = subject_split(subjects * 3)
        self.assertEqual(split, subject_split(list(reversed(subjects))))
        self.assertEqual(sum(len(v) for v in split.values()), 13)
        self.assertFalse(set(split['train']) & set(split['val']))
        self.assertFalse(set(split['train']) & set(split['test']))
        self.assertFalse(set(split['test']) & set(split['val']))

    def test_csv_resume_requires_confirmed_range_and_final_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.csv'
            path.with_suffix('.part').write_bytes(b'abc')
            response = MagicMock()
            response.__enter__.return_value = response
            response.status_code = 206
            response.headers = {'Content-Range': 'bytes 3-5/6'}
            response.iter_content.return_value = [b'def']
            with patch('acquire_tongue_posture_open.requests.get', return_value=response) as request:
                download_csv('https://example.com/data.csv', path, 6, hashlib.md5(b'abcdef').hexdigest())
            self.assertEqual(request.call_args.kwargs['headers'], {'Range': 'bytes=3-'})
            self.assertEqual(path.read_bytes(), b'abcdef')

    def test_csv_wrong_resume_range_keeps_partial_and_never_promotes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.csv'
            path.with_suffix('.part').write_bytes(b'abc')
            response = MagicMock()
            response.__enter__.return_value = response
            response.status_code = 206
            response.headers = {'Content-Range': 'bytes 2-5/6'}
            with patch('acquire_tongue_posture_open.requests.get', return_value=response):
                with self.assertRaises(ValueError):
                    download_csv('https://example.com/data.csv', path, 6, 'irrelevant')
            self.assertFalse(path.exists())
            self.assertEqual(path.with_suffix('.part').read_bytes(), b'abc')
