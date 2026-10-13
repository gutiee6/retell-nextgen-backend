"""Offline tests for the Retell webhook scaffold; no vendor calls or patient data."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app


class RetellBackendTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app)

    def test_health_is_configuration_only(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "ok",
            "mode": "configuration_only",
        })

    def test_webhook_fails_closed_without_credentials(self):
        with patch.dict("os.environ", {"RETELL_API_KEY": ""}):
            response = self.client.post("/retell/webhook", content=b"{}")
        self.assertEqual(response.status_code, 401)

    def test_webhook_rejects_invalid_signature(self):
        with patch.dict("os.environ", {"RETELL_API_KEY": "test-only"}):
            with patch.object(app, "Retell") as retell:
                retell.return_value.verify.return_value = False
                response = self.client.post(
                    "/retell/webhook",
                    content=b'{"event":"call_ended"}',
                    headers={"x-retell-signature": "invalid-test-signature"},
                )
        self.assertEqual(response.status_code, 401)

    def test_webhook_rejects_oversized_payload(self):
        with patch.dict("os.environ", {"RETELL_API_KEY": "test-only"}):
            with patch.object(app, "Retell") as retell:
                retell.return_value.verify.return_value = True
                response = self.client.post(
                    "/retell/webhook",
                    content=b"x" * 100_001,
                    headers={"x-retell-signature": "synthetic-test-signature"},
                )
        self.assertEqual(response.status_code, 413)

    def test_verified_webhook_returns_no_content(self):
        with patch.dict("os.environ", {"RETELL_API_KEY": "test-only"}):
            with patch.object(app, "Retell") as retell:
                retell.return_value.verify.return_value = True
                response = self.client.post(
                    "/retell/webhook",
                    content=b'{"event":"call_ended"}',
                    headers={"x-retell-signature": "synthetic-test-signature"},
                )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def test_office_routing_requires_bearer_token(self):
        with patch.dict("os.environ", {"FUNCTION_BEARER_TOKEN": "test-token"}):
            response = self.client.post("/retell/functions/office-routing")
        self.assertEqual(response.status_code, 401)

    def test_office_routing_returns_generic_nonclinical_data(self):
        with patch.dict("os.environ", {"FUNCTION_BEARER_TOKEN": "test-token"}):
            response = self.client.post(
                "/retell/functions/office-routing",
                headers={"Authorization": "Bearer test-token"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["practice"], "Nevada Brain & Spine Care")
        self.assertEqual(response.json()["office_hours"], "Not confirmed; transfer to staff for current hours.")
        self.assertIn("Do not triage", response.json()["clinical_policy"])


if __name__ == "__main__":
    unittest.main()
