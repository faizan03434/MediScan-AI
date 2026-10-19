import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app


class LivenessTests(unittest.TestCase):
    def test_probe_does_not_require_torch_or_claim_clinical_readiness(self):
        with patch.dict(sys.modules, {'torch': None}):
            response = TestClient(app).get('/health/live')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'running', 'clinical_inference_enabled': False})
