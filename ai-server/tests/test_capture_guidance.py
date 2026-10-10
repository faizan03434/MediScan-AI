import io
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from main import app
from services.capture_guidance import guide


class CaptureGuidanceTests(unittest.TestCase):
    def textured(self):
        rng = np.random.default_rng(5)
        return Image.fromarray(rng.integers(50, 200, (240, 320, 3), dtype=np.uint8))

    def test_quality_is_not_body_part_or_disease_recognition(self):
        result = guide(self.textured(), 'skin')
        self.assertTrue(result['capture_eligible'])
        self.assertFalse(result['target_verified'])
        self.assertFalse(result['clinical_inference'])
        self.assertFalse(result['preview_stored'])
        self.assertEqual(len(result['signal']), 64)

    def test_blank_or_dark_frames_cannot_auto_capture(self):
        for value in (0, 128, 255):
            self.assertFalse(guide(Image.new('RGB', (320, 240), (value,)*3), 'skin')['capture_eligible'])

    def test_posture_needs_one_unclipped_person_not_just_quality(self):
        for box, kind in [(None, 'unavailable'), (None, 'multiple_people'),
                          ({'x': 0, 'y': .1, 'width': .4, 'height': .8}, 'yolov8n-person')]:
            self.assertFalse(guide(self.textured(), 'posture', lambda _: (box, kind))['capture_eligible'])
        result = guide(self.textured(), 'posture', lambda _: ({'x': .2, 'y': .1, 'width': .4, 'height': .8}, 'yolov8n-person'))
        self.assertTrue(result['target_verified'])
        self.assertFalse(result['clinical_inference'])

    def test_route_auth_size_format_and_unknown_module(self):
        client = TestClient(app)
        raw = io.BytesIO()
        self.textured().save(raw, 'PNG')
        headers = {'Authorization': 'Bearer capture-fixture-key'}
        with patch('utils.auth_utils.get_settings') as settings:
            settings.return_value.api_key = 'capture-fixture-key'
            self.assertEqual(client.post('/api/v1/capture/skin', files={'image': ('x.png', raw.getvalue(), 'image/png')}).status_code, 401)
            self.assertEqual(client.post('/api/v1/capture/skin', headers=headers, files={'image': ('x.png', b'x' * (1024*1024+1), 'image/png')}).status_code, 413)
            self.assertEqual(client.post('/api/v1/capture/skin', headers=headers, files={'image': ('x.png', b'bad', 'image/png')}).status_code, 422)
            self.assertEqual(client.post('/api/v1/capture/retina', headers=headers, files={'image': ('x.png', raw.getvalue(), 'image/png')}).status_code, 404)
            result = client.post('/api/v1/capture/skin', headers=headers, files={'image': ('x.png', raw.getvalue(), 'image/png')})
            self.assertEqual(result.status_code, 200)
            self.assertFalse(result.json()['clinical_inference'])
