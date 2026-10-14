"""Synthetic, offline tests. No patient data or external requests."""
import os
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from office_mcp import (
    app,
    appointment_guidance,
    department_guidance,
    has_valid_mcp_token,
    integration_capabilities,
    office_information,
)


class PublicOfficeMCPTests(unittest.TestCase):
    def test_booking_link_is_canonical(self):
        info = office_information()
        self.assertIn("yourhealthfile.com/providers/1289988/", info["new_patient_booking_url"])
        self.assertIn("No appointment", info["appointment_status"])

    def test_spanish_is_available(self):
        info = office_information("es")
        self.assertEqual(info["language"], "es")
        self.assertIn("cita", info["message"].lower())

    def test_no_scheduling_action_is_claimed(self):
        for request_type in ("new", "availability", "reschedule", "cancel"):
            result = appointment_guidance(request_type)
            self.assertFalse(result["live_availability_checked"])
            self.assertFalse(result["appointment_booked"])
            self.assertFalse(result["appointment_changed"])
            self.assertFalse(result["appointment_cancelled"])
            self.assertTrue(result["staff_confirmation_required"])

    def test_transfers_are_not_claimed(self):
        guidance = department_guidance("surgery_scheduling")
        self.assertFalse(guidance["transfer_performed"])
        self.assertFalse(guidance["staff_contacted"])

    def test_no_ehr_patient_or_call_access(self):
        status = integration_capabilities()
        self.assertFalse(status["nextgen_api_connected"])
        self.assertFalse(status["patient_data_access"])
        self.assertFalse(status["call_analytics_connected"])

    def test_missing_token_fails_closed(self):
        with patch.dict(os.environ, {"MCP_BEARER_TOKEN": ""}):
            self.assertFalse(has_valid_mcp_token(""))
            self.assertFalse(has_valid_mcp_token("Bearer not-a-token"))
            client = TestClient(app)
            self.assertEqual(client.post("/mcp", json={}).status_code, 401)

    def test_short_token_is_rejected(self):
        with patch.dict(os.environ, {"MCP_BEARER_TOKEN": "short"}):
            self.assertFalse(has_valid_mcp_token("Bearer short"))

    def test_proper_token_is_accepted(self):
        secret = "synthetic-testing-secret-" + "x" * 40
        with patch.dict(os.environ, {"MCP_BEARER_TOKEN": secret}):
            self.assertTrue(has_valid_mcp_token("Bearer " + secret))
            self.assertFalse(has_valid_mcp_token("Bearer " + secret[:-1]))

    def test_health_check_without_token(self):
        with patch.dict(os.environ, {"MCP_BEARER_TOKEN": ""}):
            with TestClient(app) as client:
                response = client.get("/health")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["mode"], "read_only_public_information")


if __name__ == "__main__":
    unittest.main()
