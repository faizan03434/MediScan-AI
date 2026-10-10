import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from acquire_medical_research import acquire  # noqa: E402


class SerialResumeTests(unittest.TestCase):
    def prepare(self, root, etag):
        directory = root / 'datasets/kaggle/retina_eye_classification_v1'
        chunks = directory / 'chunks'
        chunks.mkdir(parents=True)
        (directory / 'audit').mkdir()
        (chunks / 'source.json').write_text(json.dumps({'bytes': 4, 'etag': 'original', 'chunk_size': 2}))
        (chunks / '0000.bin').write_bytes(b'AB')
        (chunks / '0000.sha256').write_text(hashlib.sha256(b'AB').hexdigest())
        (chunks / '0001.bin').write_bytes(b'XX')
        (chunks / '0001.sha256').write_text(hashlib.sha256(b'CD').hexdigest())
        metadata = MagicMock()
        metadata.json.return_value = {'currentVersionNumber': 1, 'licenseName': 'fixture'}
        probe = MagicMock()
        probe.__enter__.return_value = probe
        probe.status_code = 206
        probe.headers = {'ETag': etag, 'Content-Range': 'bytes 0-0/4'}
        return directory, metadata, probe

    def test_changed_source_cannot_seed_old_chunks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory, metadata, probe = self.prepare(root, 'changed')
            with patch('acquire_medical_research.ROOT', root), \
                    patch('acquire_medical_research.get_with_retry', side_effect=[metadata, probe]), \
                    patch('acquire_medical_research.download') as download:
                with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                    acquire('retina_eye_classification', serial=True)
            download.assert_not_called()
            self.assertFalse((directory / 'source.zip.part').exists())

    def test_only_hash_verified_contiguous_prefix_is_seeded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory, metadata, probe = self.prepare(root, 'original')
            def fake_download(url, archive, **kwargs):
                self.assertEqual(archive.with_suffix('.zip.part').read_bytes(), b'AB')
                archive.write_bytes(b'archive fixture')
            with patch('acquire_medical_research.ROOT', root), \
                    patch('acquire_medical_research.get_with_retry', side_effect=[metadata, probe]), \
                    patch('acquire_medical_research.download', side_effect=fake_download), \
                    patch('acquire_medical_research.safe_extract', return_value=0), \
                    patch('acquire_medical_research.audit', return_value={}):
                acquire('retina_eye_classification', serial=True)
            self.assertEqual((directory / 'source.zip.part').read_bytes(), b'AB')
