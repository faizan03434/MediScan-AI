import io
import unittest
from unittest.mock import patch

import numpy as np
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from PIL import Image

from utils.auth_utils import verify_api_key
from utils.image_utils import pil_from_bytes, read_image_from_bytes


class ImageUploadSecurityTests(unittest.TestCase):
    def encode(self, image, format='PNG', **options):
        buffer = io.BytesIO()
        image.save(buffer, format=format, **options)
        return buffer.getvalue()

    def test_pixel_budget_rejected_before_decode(self):
        raw = self.encode(Image.new('RGB', (5, 5)))
        with patch('utils.image_utils.MAX_DECODED_PIXELS', 24), patch.object(Image.Image, 'load') as load:
            with self.assertRaises(HTTPException) as error:
                pil_from_bytes(raw)
            self.assertEqual(error.exception.status_code, 413)
            load.assert_not_called()

    def test_orientation_applied_and_private_metadata_removed(self):
        image = Image.new('RGB', (12, 6))
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = 'private patient fixture'
        result = pil_from_bytes(self.encode(image, 'JPEG', exif=exif))
        self.assertEqual(result.size, (6, 12))
        self.assertEqual(result.mode, 'RGB')
        self.assertFalse(result.info)
        self.assertFalse(result.getexif())

    def test_content_type_cannot_disguise_unsupported_format(self):
        with self.assertRaises(HTTPException) as error:
            pil_from_bytes(self.encode(Image.new('RGB', (4, 4)), 'GIF'))
        self.assertEqual(error.exception.status_code, 415)

    def test_corrupt_upload_does_not_leak_decoder_details(self):
        with self.assertRaises(HTTPException) as error:
            pil_from_bytes(b'not an image')
        self.assertEqual(error.exception.detail, 'Invalid image format.')

    def test_opencv_cannot_bypass_pixel_budget(self):
        with patch('utils.image_utils.MAX_DECODED_PIXELS', 24):
            with self.assertRaises(HTTPException):
                read_image_from_bytes(self.encode(Image.new('RGB', (5, 5))))

    def test_opencv_retains_expected_bgr_order(self):
        array = read_image_from_bytes(self.encode(Image.new('RGB', (3, 3), (255, 0, 0))))
        np.testing.assert_array_equal(array[0, 0], [0, 0, 255])

    def test_empty_and_unicode_keys_fail_closed(self):
        for configured, supplied in [('', ''), ('expected', 'wrong'), ('expected', '\u2603')]:
            with patch('utils.auth_utils.get_settings') as settings:
                settings.return_value.api_key = configured
                with self.assertRaises(HTTPException) as error:
                    verify_api_key(HTTPAuthorizationCredentials(scheme='Bearer', credentials=supplied))
                self.assertEqual(error.exception.status_code, 401)

    def test_valid_key_remains_accepted(self):
        with patch('utils.auth_utils.get_settings') as settings:
            settings.return_value.api_key = 'fixture-only'
            self.assertEqual(verify_api_key(HTTPAuthorizationCredentials(scheme='Bearer', credentials='fixture-only')), 'fixture-only')
