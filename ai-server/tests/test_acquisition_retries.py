import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from acquire_skin_kaggle import get_with_retry  # noqa: E402


class AcquisitionRetryTests(unittest.TestCase):
    @patch('acquire_skin_kaggle.time.sleep')
    @patch('acquire_skin_kaggle.requests.get')
    def test_transient_connection_errors_retry_without_changing_arguments(self, get, sleep):
        get.side_effect = [requests.ConnectionError(), 'response']
        self.assertEqual(get_with_retry('source', stream=True, timeout=5), 'response')
        self.assertEqual(get.call_count, 2)
        get.assert_called_with('source', stream=True, timeout=5)
        sleep.assert_called_once_with(1)

    @patch('acquire_skin_kaggle.time.sleep')
    @patch('acquire_skin_kaggle.requests.get', side_effect=requests.Timeout())
    def test_transport_failure_is_bounded_and_validation_errors_do_not_retry(self, get, sleep):
        with self.assertRaises(requests.Timeout):
            get_with_retry('source')
        self.assertEqual(get.call_count, 3)
        get.reset_mock()
        get.side_effect = ValueError('Invalid range')
        with self.assertRaises(ValueError):
            get_with_retry('source')
        self.assertEqual(get.call_count, 1)
