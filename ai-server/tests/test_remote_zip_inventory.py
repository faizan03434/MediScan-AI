import unittest
from unittest.mock import MagicMock, patch

from training.inspect_kaggle_archive import RangeZip


def response(status, header, chunks=()):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status_code = status
    result.headers = {'Content-Range': header}
    result.url = 'https://example.invalid/archive'
    result.iter_content.return_value = iter(chunks)
    return result


class RemoteZipTests(unittest.TestCase):
    def reader(self, body):
        session = MagicMock()
        session.get.side_effect = [response(206, 'bytes 0-0/100'), body]
        return session

    def test_ignored_range_never_consumes_full_response(self):
        body = response(200, '')
        with patch('training.inspect_kaggle_archive.requests.Session', return_value=self.reader(body)):
            with RangeZip('source') as reader:
                with self.assertRaises(ValueError):
                    reader.read(3)
        body.iter_content.assert_not_called()

    def test_truncated_and_oversized_bodies_fail(self):
        for chunks in ([b'a'], [b'abcd']):
            with patch('training.inspect_kaggle_archive.requests.Session', return_value=self.reader(response(206, 'bytes 0-2/100', chunks))):
                with RangeZip('source') as reader:
                    with self.assertRaises(ValueError):
                        reader.read(3)
                    self.assertEqual(reader.tell(), 0)

    def test_valid_range_and_seek_boundaries(self):
        with patch('training.inspect_kaggle_archive.requests.Session', return_value=self.reader(response(206, 'bytes 0-2/100', [b'abc']))):
            with RangeZip('source') as reader:
                self.assertEqual(reader.read(3), b'abc')
                self.assertEqual(reader.seek(-5, 2), 95)
                with self.assertRaises(ValueError):
                    reader.seek(101)
