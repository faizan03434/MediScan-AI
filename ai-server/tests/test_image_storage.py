import asyncio
import io
import unittest
from unittest.mock import patch
from PIL import Image, PngImagePlugin
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from routers.image_storage import normalize
from utils.image_workload import image_slot


class ImageStorageTests(unittest.TestCase):
    def private_photo(self):
        image = Image.new('RGB', (2, 3), (20, 80, 130))
        exif = image.getexif()
        exif[274] = 6
        exif[315] = 'private identity'
        text = PngImagePlugin.PngInfo()
        text.add_text('patient', 'private identity')
        output = io.BytesIO()
        image.save(output, format='PNG', pnginfo=text, exif=exif, dpi=(300, 300))
        return output.getvalue()

    def test_stored_bytes_are_oriented_and_metadata_free(self):
        result = normalize(self.private_photo())
        with Image.open(io.BytesIO(result)) as image:
            self.assertEqual(image.format, 'PNG')
            self.assertEqual(image.size, (3, 2))
            self.assertFalse(image.info)
            self.assertFalse(image.getexif())
            self.assertEqual(image.getpixel((0, 0)), (20, 80, 130))
        self.assertNotIn(b'private identity', result)

    def test_invalid_and_oversized_output_fail_closed(self):
        with self.assertRaises(HTTPException):
            normalize(b'not a photo')
        with patch('routers.image_storage.MAX_OUTPUT', 32), self.assertRaises(HTTPException) as error:
            normalize(self.private_photo())
        self.assertEqual(error.exception.status_code, 413)

    def test_private_route_auth_limits_and_no_cache(self):
        client = TestClient(app)
        photo = {'image': ('x.png', self.private_photo(), 'image/png')}
        headers = {'Authorization': 'Bearer storage-fixture-key'}
        with patch('utils.auth_utils.get_settings') as settings:
            settings.return_value.api_key = 'storage-fixture-key'
            self.assertEqual(client.post('/api/v1/images/normalize', files=photo).status_code, 401)
            response = client.post('/api/v1/images/normalize', headers=headers, files=photo)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            with patch('routers.image_storage.MAX_INPUT', 32):
                self.assertEqual(client.post('/api/v1/images/normalize', headers=headers, files=photo).status_code, 413)

    def test_image_capacity_is_bounded_and_released_on_error(self):
        async def exercise():
            async with image_slot():
                async with image_slot():
                    with self.assertRaises(HTTPException) as error:
                        async with image_slot():
                            self.fail('Capacity limit bypassed')
                    self.assertEqual(error.exception.status_code, 429)
            with self.assertRaises(ValueError):
                async with image_slot():
                    raise ValueError('fixture')
            async with image_slot():
                async with image_slot():
                    pass
        asyncio.run(exercise())
