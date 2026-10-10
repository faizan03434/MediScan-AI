import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from acquire_fuseg_original import git_blob_sha, target_path  # noqa: E402


class FUSegSourceTests(unittest.TestCase):
    def test_source_hash_includes_git_object_header(self):
        data = b'sample image bytes'
        self.assertEqual(git_blob_sha(data), hashlib.sha1(b'blob 18\0' + data).hexdigest())
        self.assertNotEqual(git_blob_sha(data), hashlib.sha1(data).hexdigest())

    def test_repository_path_cannot_escape_workspace_dataset_root(self):
        root = Path(__file__).resolve().parent
        for relative in ('../outside', '/outside', 'C:/outside', 'train\\outside'):
            with self.assertRaises(ValueError):
                target_path(root, relative)
        self.assertEqual(target_path(root, 'train/images/sample.png'), root / 'train/images/sample.png')
