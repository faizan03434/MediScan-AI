import io
import unittest
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient
from main import app
from services.document_ocr import extract

class DocumentTests(unittest.TestCase):
    def setUp(self):
        raw = io.BytesIO()
        Image.new('RGB', (100, 80), 'white').save(raw, format='PNG')
        self.raw = raw.getvalue()
        self.client = TestClient(app)
        self.headers = {'Authorization': 'Bearer internal-dev-key'}
    def send(self, raw=None, headers=None):
        return self.client.post('/api/v1/documents/ocr', headers=self.headers if headers is None else headers,
            files={'image': ('label.png', self.raw if raw is None else raw, 'image/png')})
    def test_auth(self):
        self.assertIn(self.send(headers={}).status_code, [401, 403])
    def test_invalid_photo(self):
        self.assertEqual(self.send(b'invalid').status_code, 422)
    @patch('routers.document_ocr.extract', side_effect=FileNotFoundError)
    def test_missing_weights_safe_unavailable(self, _):
        self.assertEqual(self.send().status_code, 503)
    @patch('services.document_ocr.reader')
    def test_text_is_unverified_and_confidence_is_ocr_only(self, mock):
        mock.return_value.readtext.return_value = [([[0,0],[100,0],[100,20],[0,20]], 'Paracetamol 500 mg', .7)]
        result = extract(self.raw)
        self.assertEqual(result['text'], 'Paracetamol 500 mg')
        self.assertTrue(result['lines'][0]['needs_review'])
        self.assertFalse(result['prescription_verified'])
        self.assertEqual(result['status'], 'requires_confirmation')
        self.assertEqual(result['lines'][0]['box'][2], [1.0, .25])
    @patch('services.document_ocr.reader')
    def test_empty_output_allows_manual_review(self, mock):
        mock.return_value.readtext.return_value = []
        self.assertEqual(extract(self.raw)['status'], 'no_text')

if __name__ == '__main__':
    unittest.main()
