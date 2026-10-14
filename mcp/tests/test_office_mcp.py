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

    def test_urgent_postop_is_routing_only_with_emergency_language(self):
        route = department_guidance("urgent_postop", language="en")
        self.assertEqual(route["department"], "urgent_postop")
        self.assertIn("dial 911", route["emergency_message"])
        self.assertFalse(route["transfer_performed"])
        self.assertFalse(route["staff_contacted"])
        self.assertNotIn("phone_number", route)
        route_es = department_guidance("urgent_postop", language="es")
        self.assertIn("911", route_es["emergency_message"])

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

    def test_root_health_for_render_probes(self):
        with patch.dict(os.environ, {"MCP_BEARER_TOKEN": ""}):
            client = TestClient(app)
            response = client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")
            self.assertEqual(client.head("/").status_code, 200)
            self.assertEqual(client.head("/health").status_code, 200)
            # The public health check must never expose MCP tool discovery.
            self.assertEqual(client.post("/mcp", json={}).status_code, 401)

    def test_authorized_mcp_initialize_and_tool_discovery(self):
        """Exercise the actual MCP transport, not just Python helper functions."""
        secret = "synthetic-mcp-test-key-" + "z" * 40
        headers = {
            "Authorization": "Bearer " + secret,
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        with patch.dict(os.environ, {"MCP_BEARER_TOKEN": secret}):
            with TestClient(app) as client:
                initialized = client.post("/mcp", headers=headers, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "synthetic-mcp-test", "version": "1"},
                    },
                })
                self.assertEqual(initialized.status_code, 200, initialized.text)
                self.assertIn("result", initialized.json(), initialized.text)
                version = initialized.json()["result"]["protocolVersion"]
                listing = client.post("/mcp", headers={
                    **headers, "Mcp-Protocol-Version": version,
                }, json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                })
                self.assertEqual(listing.status_code, 200, listing.text)
                names = {tool["name"] for tool in listing.json()["result"]["tools"]}
                self.assertEqual(names, {
                    "get_office_information",
                    "get_appointment_guidance",
                    "get_department_routing",
                    "get_integration_status",
                })

    def test_health_check_without_token(self):
        with patch.dict(os.environ, {"MCP_BEARER_TOKEN": ""}):
            client = TestClient(app)
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["mode"], "read_only_public_information")


if __name__ == "__main__":
    unittest.main()
