"""Read-only Retell MCP server: public office information, never patient data."""
from contextlib import asynccontextmanager
from datetime import datetime
import os
import secrets
from typing import Literal

from mcp.server import MCPServer
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route


from office_policy import (
    BOOKING_URL, PRACTICE, OFFICE_ADDRESS, OFFICE_LOCATION_NOTE,
    OFFICE_PHONE, OFFICE_EMAIL, PHONE_HOURS, FRIDAY_CLINIC_HOURS,
    HOURS_APPROVAL_REQUIRED, phone_status,
    administrative_guidance as policy_administrative_guidance,
)

mcp = MCPServer(
    "Nevada Brain & Spine public office information",
    instructions=(
        "Public information only. Do not request patient identifiers or clinical "
        "details. Never claim to have checked availability, booked, changed, or "
        "cancelled an appointment. Route all patient-specific requests to the "
        "practice's approved staff workflow."
    ),
)


def office_information(language: Literal["en", "es"] = "en") -> dict:
    """Public directions/contact and provisional hours, not proof of staffing."""
    if language == "es":
        msg = (
            "Para citas nuevas, utilice YourHealthFile. Los cambios o "
            "cancelaciones deben ser confirmados por el personal."
        )
        hours_notice = (
            "Horario telefónico propuesto de lunes a viernes, 7 a. m. "
            "hasta antes de las 11 a. m. (hora del Pacífico); "
            "requiere confirmación del consultorio."
        )
        shared = (
            "Oficina compartida con la práctica del Dr. Forte; "
            "este asistente representa a Nevada Brain & Spine Care."
        )
    else:
        msg = (
            "For new appointments, use the YourHealthFile patient portal. "
            "Staff must confirm changes or cancellations."
        )
        hours_notice = (
            "Proposed staffed phone window: Monday-Friday 7 AM to before "
            "11 AM Pacific, pending practice confirmation. Friday in-person "
            "clinic 7 AM-noon does not extend live phone coverage."
        )
        shared = OFFICE_LOCATION_NOTE
    return {
        "practice": PRACTICE,
        "language": language,
        "new_patient_booking_url": BOOKING_URL,
        "portal_name": "YourHealthFile",
        "message": msg,
        "office_address_on_file": OFFICE_ADDRESS,
        "shared_office_note": shared,
        "office_phone_on_file": OFFICE_PHONE,
        "office_email_on_file": OFFICE_EMAIL,
        "phone_hours": PHONE_HOURS,
        "friday_in_person_clinic_hours": FRIDAY_CLINIC_HOURS,
        "hours_notice": hours_notice,
        "office_hours_verified": not HOURS_APPROVAL_REQUIRED,
        "current_staff_availability_verified": False,
        "appointment_status": (
            "No se ha reservado ninguna cita mediante esta herramienta."
            if language == "es"
            else "No appointment has been booked by this tool."
        ),
    }

def appointment_guidance(
    request_type: Literal["new", "availability", "reschedule", "cancel"],
    language: Literal["en", "es"] = "en",
) -> dict:
    """Give safe instructions; does not perform any scheduling action."""
    if language == "es":
        messages = {
            "new": "Abra el enlace de YourHealthFile para ver las opciones de citas nuevas.",
            "availability": "Consulte la disponibilidad directamente en YourHealthFile. Esta herramienta no puede ver horarios en tiempo real.",
            "reschedule": "Solicite el cambio por el canal autorizado de la oficina. Esta herramienta no puede reprogramar.",
            "cancel": "Solicite la cancelación por el canal autorizado de la oficina. Esta herramienta no puede cancelar.",
        }
    else:
        messages = {
            "new": "Open YourHealthFile to view new-patient appointment options.",
            "availability": "Check available times directly in YourHealthFile; this tool has no live calendar access.",
            "reschedule": "Use the approved office staff workflow. This tool cannot reschedule an appointment.",
            "cancel": "Use the approved office staff workflow. This tool cannot cancel an appointment.",
        }
    return {
        "request_type": request_type,
        "language": language,
        "instructions": messages[request_type],
        "portal_name": "YourHealthFile",
        "new_patient_booking_url": BOOKING_URL,
        "live_availability_checked": False,
        "appointment_booked": False,
        "appointment_changed": False,
        "appointment_cancelled": False,
        "staff_confirmation_required": True,
    }


DEPARTMENTS = {
    "office_information": "Public office information",
    "surgery_scheduling": "Surgery scheduling staff",
    "medical_records_referrals": "Medical records and referrals staff",
    "tms": "TMS program staff",
    "appointments": "Appointment staff",
    "urgent_postop": "Urgent postoperative call transfer (practice-approved physician destination)",
    "office_staff": "General office staff",
}


def department_guidance(
    department: Literal[
        "office_information",
        "surgery_scheduling",
        "medical_records_referrals",
        "tms",
        "appointments",
        "urgent_postop",
        "office_staff",
    ],
    language: Literal["en", "es"] = "en",
) -> dict:
    """Identify routing destination, without calling or promising a transfer."""
    return {
        "department": department,
        "description": DEPARTMENTS[department],
        "emergency_message": (
            "For a life-threatening emergency, hang up and dial 911 immediately."
            if department == "urgent_postop" and language == "en" else
            "Si es una emergencia que pone en peligro la vida, cuelgue y llame al 911 inmediatamente."
            if department == "urgent_postop" else None
        ),
        "language": language,
        "transfer_performed": False,
        "staff_contacted": False,
        "instruction": (
            "Use only the transfer destination approved and configured in Retell. "
            "If unavailable, explain that staff cannot be connected right now."
            if language == "en"
            else "Use únicamente la transferencia aprobada y configurada en Retell. Si no está disponible, indique que no puede conectar con el personal en este momento."
        ),
    }


def integration_capabilities() -> dict:
    """Accurately describe current capabilities, not desired future ones."""
    return {
        "mode": "read_only_public_information",
        "retell_mcp_tools_available": True,
        "nextgen_api_connected": False,
        "live_appointment_availability": False,
        "appointment_booking_enabled": False,
        "appointment_changes_enabled": False,
        "patient_data_access": False,
        "call_analytics_connected": False,
        "secure_message_intake_enabled": False,
        "records_release_enabled": False,
        "fax_transmission_enabled": False,
        "actual_retell_transfer_executed": False,
        "notes": "No EHR, patient, call transcript, SMS or scheduling access is implemented.",
    }


def staffed_phone_window_guidance(
    language: Literal["en", "es"] = "en",
    when: datetime | None = None,
) -> dict:
    """Local Pacific schedule calculation, not verification of real staffing."""
    status = phone_status(when)
    window = status["live_phone_staff_available"]
    if language == "es":
        guidance = (
            "Según el horario telefónico propuesto, no hay atención telefónica "
            "en vivo ahora. Puede utilizar un canal de contacto autorizado."
            if not window else
            "Según el horario propuesto, se encuentra dentro de las horas "
            "telefónicas. La disponibilidad real del personal no está verificada."
        )
    else:
        guidance = (
            "You are calling outside the proposed staffed phone hours. "
            "Live phone staff are not scheduled under this policy; "
            "use an approved contact or message channel."
            if not window else
            "This is within the proposed staffed phone window; actual live "
            "staff availability is not verified."
        )
    return {
        "language": language,
        "timezone": status["timezone"],
        "local_time": status["local_time"],
        "phone_hours": PHONE_HOURS,
        "friday_in_person_clinic_hours": FRIDAY_CLINIC_HOURS,
        "within_proposed_staffed_window": window,
        "friday_in_person_clinic_active": status["friday_in_person_clinic_active"],
        "office_hours_verified": not HOURS_APPROVAL_REQUIRED,
        "actual_staff_availability_verified": False,
        "spoken_guidance": guidance,
        "message_submitted": False,
    }


def request_processing_guidance(
    request_type: Literal[
        "medical_records", "fax", "referral", "outgoing_referral",
        "forms", "billing", "refill", "dose_change", "other",
    ],
    language: Literal["en", "es"] = "en",
) -> dict:
    """No caller data accepted; no records, faxes or messages are transmitted."""
    result = policy_administrative_guidance(request_type, language)
    return {
        **result,
        "office_contact_on_file": OFFICE_PHONE,
        "message_submission_available_from_this_tool": False,
        "callers_must_use_approved_secure_intake": True,
    }

@mcp.tool()
def get_office_information(language: Literal["en", "es"] = "en") -> dict:
    """Get public office information and the new-patient booking link."""
    return office_information(language)


@mcp.tool()
def get_appointment_guidance(
    request_type: Literal["new", "availability", "reschedule", "cancel"],
    language: Literal["en", "es"] = "en",
) -> dict:
    """Get appointment instructions without reading or editing any appointment."""
    return appointment_guidance(request_type, language)


@mcp.tool()
def get_department_routing(
    department: Literal[
        "office_information",
        "surgery_scheduling",
        "medical_records_referrals",
        "tms",
        "appointments",
        "urgent_postop",
        "office_staff",
    ],
    language: Literal["en", "es"] = "en",
) -> dict:
    """Return a routing category; urgent post-op callers still need a Retell transfer."""
    return department_guidance(department, language)


@mcp.tool()
def get_phone_hours_status(language: Literal["en", "es"] = "en") -> dict:
    """Get current Pacific-time proposed phone window, not confirmed staff presence."""
    return staffed_phone_window_guidance(language)


@mcp.tool()
def get_administrative_request_guidance(
    request_type: Literal[
        "medical_records", "fax", "referral", "outgoing_referral",
        "forms", "billing", "refill", "dose_change", "other",
    ],
    language: Literal["en", "es"] = "en",
) -> dict:
    """Get records/fax/referral/refill processing targets, without taking requests."""
    return request_processing_guidance(request_type, language)

@mcp.tool()
def get_integration_status() -> dict:
    """Report which integrations are actually implemented."""
    return integration_capabilities()


async def health(_request):
    return JSONResponse({"status": "ok", "mode": "read_only_public_information"})


@asynccontextmanager
async def lifespan(_app):
    # Mounted ASGI apps do not run their own lifespan automatically.
    async with mcp.session_manager.run():
        yield


# Set host for a remotely deployed server; MCP requires a separate bearer token.
mcp_http_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    max_request_body_size=16_384,
    host="0.0.0.0",
)
inner_app = Starlette(
    routes=[
        Route("/health", health, methods=["GET", "HEAD"]),
        Route("/", health, methods=["GET", "HEAD"]),
        Mount("/", app=mcp_http_app),
    ],
    lifespan=lifespan,
)


def has_valid_mcp_token(auth_header: str) -> bool:
    """Fail closed without a unique, sufficiently long secret."""
    token = os.getenv("MCP_BEARER_TOKEN", "")
    return len(token) >= 32 and secrets.compare_digest(auth_header, "Bearer " + token)


class BearerTokenGate:
    """Protect all routes except the public health check, including tool discovery."""
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path") not in {"/health", "/"}:
            headers = dict(scope.get("headers", []))
            provided = headers.get(b"authorization", b"").decode("latin-1")
            if not has_valid_mcp_token(provided):
                response = PlainTextResponse("Unauthorized", status_code=401)
                return await response(scope, receive, send)
        return await self.asgi_app(scope, receive, send)


app = BearerTokenGate(inner_app)
