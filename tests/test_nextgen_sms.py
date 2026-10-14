"""Synthetic-only, offline tests. No messages or data leave the test process."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app
from nextgen_sms import SmsPreviewRequest, preview_sms

client = TestClient(app)


class SmsPreviewTests(unittest.TestCase):
    def test_requires_token(self):
        with patch.dict("os.environ", {"NEXTGEN_SMS_PREVIEW_TOKEN": "test-token"}):
            response = client.post("/nextgen/sms/preview", json={
                "action": "cancelled", "consent_verified": True
            })
        self.assertEqual(response.status_code, 401)

    def test_not_configured_fails_closed(self):
        with patch.dict("os.environ", {"NEXTGEN_SMS_PREVIEW_TOKEN": ""}):
            response = client.post(
                "/nextgen/sms/preview",
                headers={"Authorization": "Bearer test-token"},
                json={"action": "cancelled", "consent_verified": True},
            )
        self.assertEqual(response.status_code, 401)

    def test_rejects_patient_fields(self):
        with patch.dict("os.environ", {"NEXTGEN_SMS_PREVIEW_TOKEN": "test-token"}):
            response = client.post(
                "/nextgen/sms/preview",
                headers={"Authorization": "Bearer test-token"},
                json={"action": "cancelled", "consent_verified": True, "phone": "+15550000000"},
            )
        self.assertEqual(response.status_code, 422)

    def test_no_consent_fails(self):
        with patch.dict("os.environ", {"NEXTGEN_SMS_PREVIEW_TOKEN": "test-token"}):
            response = client.post(
                "/nextgen/sms/preview",
                headers={"Authorization": "Bearer test-token"},
                json={"action": "cancelled", "consent_verified": False},
            )
        self.assertEqual(response.status_code, 409)

    def test_opt_out_fails(self):
        payload = SmsPreviewRequest(action="cancelled", consent_verified=True, opted_out=True)
        with self.assertRaises(ValueError):
            preview_sms(payload)

    def test_preview_has_no_delivery(self):
        with patch.dict("os.environ", {"NEXTGEN_SMS_PREVIEW_TOKEN": "test-token"}):
            response = client.post(
                "/nextgen/sms/preview",
                headers={"Authorization": "Bearer test-token"},
                json={
                    "action": "rescheduled",
                    "start_at": "2026-11-03T18:30:00+00:00",
                    "consent_verified": True,
                },
            )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["mode"], "preview_only")
        self.assertFalse(result["sent"])
        self.assertIn("Nov 3 at 10:30 AM", result["message"])
        self.assertIn("STOP", result["message"])

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            SmsPreviewRequest(
                action="scheduled", start_at="2026-11-03T10:30:00", consent_verified=True,
            )

    def test_missing_date_rejected(self):
        with self.assertRaises(ValueError):
            preview_sms(SmsPreviewRequest(action="reminder", consent_verified=True))

    def test_status_public_non_sensitive(self):
        response = client.get("/nextgen/sms/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["sending_enabled"])


if __name__ == "__main__":
    unittest.main()
