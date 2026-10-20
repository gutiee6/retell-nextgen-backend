"""Offline regression tests for Oct 19 Retell call-routing failures."""
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

import app
from office_policy import (
    BOOKING_URL, administrative_guidance, appointment_guidance, phone_status,
)

TZ = ZoneInfo("America/Los_Angeles")


class RetellBackendTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app)
        self.auth = {"Authorization": "Bearer synthetic-test-token"}

    def post(self, path, data=None):
        with patch.dict("os.environ", {"FUNCTION_BEARER_TOKEN": "synthetic-test-token"}):
            return self.client.post(path, json={} if data is None else data, headers=self.auth)

    def test_health_is_configuration_only(self):
        self.assertEqual(self.client.get("/health").json(),
                         {"status": "ok", "mode": "configuration_only"})

    def test_root_and_head_health_probes(self):
        for method in ("GET", "HEAD"):
            for path in ("/", "/health"):
                response = self.client.request(method, path)
                self.assertEqual(response.status_code, 200, (method, path))
                if method == "GET":
                    self.assertEqual(response.json()["status"], "ok")

    def test_webhook_rejects_no_credentials(self):
        with patch.dict("os.environ", {"RETELL_API_KEY": ""}):
            self.assertEqual(self.client.post("/retell/webhook", content=b"{}").status_code, 401)

    def test_webhook_rejects_invalid_signature(self):
        with patch.dict("os.environ", {"RETELL_API_KEY": "test-only"}):
            with patch.object(app, "Retell") as retell:
                retell.return_value.verify.return_value = False
                response = self.client.post(
                    "/retell/webhook", content=b'{"event":"call_ended"}',
                    headers={"x-retell-signature": "invalid-test-signature"})
        self.assertEqual(response.status_code, 401)

    def test_webhook_rejects_oversized_body(self):
        with patch.dict("os.environ", {"RETELL_API_KEY": "test-only"}):
            with patch.object(app, "Retell") as retell:
                retell.return_value.verify.return_value = True
                response = self.client.post(
                    "/retell/webhook", content=b"x" * 100_001,
                    headers={"x-retell-signature": "synthetic-test-signature"})
        self.assertEqual(response.status_code, 413)

    def test_webhook_verified_discards_payload(self):
        with patch.dict("os.environ", {"RETELL_API_KEY": "test-only"}):
            with patch.object(app, "Retell") as retell:
                retell.return_value.verify.return_value = True
                response = self.client.post(
                    "/retell/webhook", content=b'{"event":"call_ended"}',
                    headers={"x-retell-signature": "synthetic-test-signature"})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

    def test_function_requires_authentication(self):
        self.assertEqual(self.client.post("/retell/functions/office-routing").status_code, 401)
        self.assertEqual(self.client.post("/retell/functions/appointment-info").status_code, 401)
        self.assertEqual(self.client.post("/retell/functions/request-guidance").status_code, 401)
        self.assertEqual(self.client.post("/retell/functions/submit-message").status_code, 401)

    def test_phone_closed_exactly_2_pm_pacific(self):
        before = phone_status(datetime(2026, 10, 21, 13, 59, 59, tzinfo=TZ))
        after = phone_status(datetime(2026, 10, 21, 14, 0, tzinfo=TZ))
        self.assertTrue(before["live_phone_staff_available"])
        self.assertFalse(after["live_phone_staff_available"])
        self.assertIn("unavailable", after["after_hours_message"])
        self.assertTrue(phone_status(datetime(2026, 10, 22, 10, 0, tzinfo=TZ))["live_phone_staff_available"])
        self.assertFalse(phone_status(datetime(2026, 10, 20, 12, 0, tzinfo=TZ))["live_phone_staff_available"])

    def test_friday_clinic_distinct_from_phone_hours(self):
        result = phone_status(datetime(2026, 10, 23, 13, 0, tzinfo=TZ))
        self.assertTrue(result["friday_in_person_clinic_active"])
        self.assertFalse(result["live_phone_staff_available"])
        self.assertIn("Friday", result["friday_in_person_clinic_hours"])

    def test_phone_weekends_and_before_open_are_closed(self):
        for sample in (
            datetime(2026, 10, 24, 8, 30, tzinfo=TZ),  # Saturday
            datetime(2026, 10, 21, 9, 59, tzinfo=TZ),  # Wednesday before opening
            datetime(2026, 10, 22, 9, 59, tzinfo=TZ),  # Thursday before opening
            datetime(2026, 10, 20, 10, 0, tzinfo=TZ),  # Tuesday
        ):
            self.assertFalse(phone_status(sample)["live_phone_staff_available"])

    def test_timezone_aware_datetime_required(self):
        with self.assertRaises(ValueError):
            phone_status(datetime(2026, 10, 20, 10, 0))

    def test_appointment_info_returns_portal_not_practice_site(self):
        result = self.post("/retell/functions/appointment-info",
                           {"request_type": "availability"})
        self.assertEqual(result.status_code, 200)
        data = result.json()
        self.assertEqual(data["portal_name"], "YourHealthFile")
        self.assertEqual(data["new_patient_booking_url"], BOOKING_URL)
        self.assertFalse(data["live_availability_checked"])
        self.assertFalse(data["appointment_booked"])
        self.assertFalse(data["message_submitted"])

    def test_portal_fallback_for_all_request_types(self):
        for kind in ("new", "availability", "reschedule", "cancel"):
            result = appointment_guidance(kind)
            self.assertEqual(result["new_patient_booking_url"], BOOKING_URL)
            self.assertFalse(result["appointment_changed"])
            self.assertFalse(result["appointment_cancelled"])

    def test_retell_wrapped_args_work_without_phi(self):
        result = self.post("/retell/functions/appointment-info",
                           {"name": "appointment_info", "args": {"request_type": "new"}})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["portal_name"], "YourHealthFile")

    def test_retell_wrapped_args_reject_patient_fields(self):
        result = self.post("/retell/functions/appointment-info",
                           {"args": {"request_type": "new", "patient_name": "SYNTHETIC"}})
        self.assertEqual(result.status_code, 422)

    def test_public_tools_reject_patient_details(self):
        for path in (
            "/retell/functions/office-routing",
            "/retell/functions/appointment-info",
            "/retell/functions/request-guidance",
            "/retell/functions/submit-message",
        ):
            result = self.post(path, {"patient_name": "SYNTHETIC NAME"})
            self.assertEqual(result.status_code, 422, path)

    def test_public_tools_reject_unknown_request_types(self):
        result = self.post("/retell/functions/request-guidance",
                           {"request_type": "unrecognized"})
        self.assertEqual(result.status_code, 422)

    def test_routine_requests_three_business_days_without_delivery_claim(self):
        for kind in ("medical_records", "fax", "referral", "forms",
                     "billing", "refill", "dose_change", "other"):
            result = administrative_guidance(kind)
            self.assertEqual(result["routine_processing_target_business_days"], 3)
            self.assertFalse(result["secure_intake_enabled"])
            self.assertFalse(result["message_submitted"])
            self.assertFalse(result["fax_sent"])

    def test_submission_endpoint_explicitly_fails_closed(self):
        result = self.post("/retell/functions/submit-message")
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()["success"])
        self.assertFalse(result.json()["message_submitted"])
        self.assertEqual(result.json()["status"], "not_configured")

    def test_office_routing_is_informational_only(self):
        result = self.post("/retell/functions/office-routing")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["practice"], "Nevada Brain & Spine Care")
        self.assertIn("Wednesday-Thursday, 10:00 AM-2:00 PM", result.json()["office_hours"])
        self.assertFalse(result.json()["phone_status"]["hours_require_practice_approval"])
        self.assertIn("Do not triage", result.json()["clinical_policy"])
        for destination in result.json()["departments"]:
            self.assertFalse(destination["transfer_performed"])

    def test_confirmed_practice_address_and_contact(self):
        result = self.post("/retell/functions/office-routing")
        self.assertEqual(result.status_code, 200)
        data = result.json()
        self.assertIn("9488 West Flamingo Road", data["office_address"])
        self.assertIn("Suite 100", data["office_address"])
        self.assertIn("Dr. Forte", data["shared_office_note"])
        self.assertEqual(data["office_phone"], "702-761-3742")
        self.assertEqual(data["office_email"], "office@nevadabrainandspine.com")

    def test_outgoing_referrals_have_two_day_target(self):
        result = administrative_guidance("outgoing_referral")
        self.assertEqual(result["routine_processing_target_business_days"], 2)
        self.assertFalse(result["message_submitted"])

    def test_short_link_not_assumed_verified(self):
        result = appointment_guidance("new")
        self.assertEqual(result["portal_name"], "YourHealthFile")
        self.assertEqual(result["practice_short_link"], "https://tinyurl.com/Dr-Nagy")
        self.assertFalse(result["short_link_redirect_verified"])

    def test_spanish_guidance(self):
        self.assertEqual(appointment_guidance("new", "es")["language"], "es")
        self.assertIn("tres días", administrative_guidance("fax", "es")["processing_notice"])

    def test_large_function_payload_rejected(self):
        result = self.post("/retell/functions/request-guidance",
                           {"request_type": "a" * 5000})
        self.assertEqual(result.status_code, 413)


if __name__ == "__main__":
    unittest.main()
