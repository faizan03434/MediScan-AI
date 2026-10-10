import io
import unittest
from PIL import Image
from fastapi.testclient import TestClient
from main import app


class PreviewSafetyTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        image = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(image, format="PNG")
        self.photo = image.getvalue()
        self.headers = {"Authorization": "Bearer internal-dev-key"}

    def test_all_modules_abstain(self):
        for module in ("anemia", "skin", "posture", "eye", "wound", "tongue", "retina"):
            with self.subTest(module=module):
                response = self.client.post(f"/api/v1/detect/{module}", headers=self.headers,
                    files={"image": ("test.png", self.photo, "image/png")})
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertFalse(result["details"]["clinical_inference"])
                self.assertEqual(result["confidence"], 0)
                self.assertIsNone(result["next_scan_days"])
                self.assertIn("Inconclusive", result["result"])
                if module == 'retina':
                    self.assertEqual(result['details']['expected_image_modality'], 'fundus')
                    self.assertFalse(result['details']['image_modality_verified'])

    def test_auth_required(self):
        response = self.client.post("/api/v1/detect/anemia",
            files={"image": ("test.png", self.photo, "image/png")})
        self.assertIn(response.status_code, (401, 403))

    def test_invalid_image_rejected(self):
        response = self.client.post("/api/v1/detect/anemia", headers=self.headers,
            files={"image": ("test.jpg", b"not an image", "image/jpeg")})
        self.assertEqual(response.status_code, 422)

    def test_unknown_module_rejected(self):
        response = self.client.post("/api/v1/detect/unknown", headers=self.headers,
            files={"image": ("test.png", self.photo, "image/png")})
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
