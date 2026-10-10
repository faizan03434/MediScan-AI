import json
import sys
import tempfile
import unittest
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from acquire_skin_kaggle import parallel_download  # noqa: E402


class DownloadFailureTests(unittest.TestCase):
    def test_failed_chunk_cancels_queue_and_records_resumable_status(self):
        probe = MagicMock()
        probe.status_code = 206
        probe.headers = {'Content-Range': 'bytes 0-0/2097152', 'ETag': 'fixture'}
        probe.url = 'https://example.invalid/fixture'
        probe.__enter__.return_value = probe
        failed, queued = Future(), Future()
        failed.set_exception(RuntimeError('Chunk incomplete; rerun to resume'))
        executor = MagicMock()
        executor.__enter__.return_value = executor
        executor.submit.side_effect = [failed, queued]
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'source.zip'
            with patch('acquire_skin_kaggle.get_with_retry', return_value=probe), \
                    patch('acquire_skin_kaggle.ThreadPoolExecutor', return_value=executor):
                with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                    parallel_download('https://example.invalid/fixture', destination)
            self.assertTrue(queued.cancelled())
            status = json.loads((destination.parent / 'download_progress.json').read_text())
            self.assertEqual(status['status'], 'incomplete_resume_required')
            self.assertFalse(destination.exists())
