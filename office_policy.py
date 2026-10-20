"""Public office routing policy. No patient identifiers or clinical information."""
from datetime import datetime, time
from zoneinfo import ZoneInfo

PRACTICE = "Nevada Brain & Spine Care"
OFFICE_ADDRESS = "9488 West Flamingo Road, Suite 100, Las Vegas, NV 89147"
OFFICE_LOCATION_NOTE = "Shared with Dr. Forte's family practice; this receptionist represents Nevada Brain & Spine Care only."
OFFICE_PHONE = "702-761-3742"
OFFICE_EMAIL = "office@nevadabrainandspine.com"
SHORT_BOOKING_URL = "https://tinyurl.com/Dr-Nagy"  # Office-provided; redirect not independently verified.
TIMEZONE = "America/Los_Angeles"
BOOKING_URL = (
    "https://www.yourhealthfile.com/providers/1289988/"
    "las-vegas-neurological-surgery-doctor.html"
)
PHONE_HOURS = "Wednesday-Thursday, 10:00 AM-2:00 PM Pacific"
FRIDAY_CLINIC_HOURS = "Friday, 10:00 AM-2:00 PM Pacific (in person, not phone coverage)"
# Schedule provided by the practice on Oct 20, 2026.
HOURS_APPROVAL_REQUIRED = False

REQUEST_TYPES = {
    "medical_records", "fax", "referral", "forms", "billing",
    "refill", "dose_change", "outgoing_referral", "other",
}
APPOINTMENT_TYPES = {"new", "availability", "reschedule", "cancel"}


def phone_status(when: datetime | None = None) -> dict:
    """Determine live receptionist coverage; 2:00 PM is CLOSED, not open."""
    if when is None:
        local = datetime.now(ZoneInfo(TIMEZONE))
    else:
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError("Expected a timezone-aware datetime")
        local = when.astimezone(ZoneInfo(TIMEZONE))

    weekday = local.weekday()
    clock = local.time().replace(tzinfo=None)
    staffed = weekday in {2, 3} and time(10, 0) <= clock < time(14, 0)
    friday_clinic = weekday == 4 and time(10, 0) <= clock < time(14, 0)
    return {
        "timezone": TIMEZONE,
        "local_time": local.isoformat(timespec="seconds"),
        "phone_hours": PHONE_HOURS,
        "friday_in_person_clinic_hours": FRIDAY_CLINIC_HOURS,
        "live_phone_staff_available": staffed,
        "friday_in_person_clinic_active": friday_clinic,
        "phone_closing_boundary": "2:00 PM Pacific is outside live phone hours",
        "after_hours_message": (
            "Live phone staff are unavailable right now. "
            "I can explain the approved way to leave a message."
            if not staffed else None
        ),
        "hours_require_practice_approval": HOURS_APPROVAL_REQUIRED,
    }


def appointment_guidance(request_type: str = "new", language: str = "en") -> dict:
    """Portal fallback works even when an external appointment lookup fails."""
    if request_type not in APPOINTMENT_TYPES:
        raise ValueError("Unknown appointment request type")
    if language not in {"en", "es"}:
        raise ValueError("Unsupported language")
    instructions = {
        "en": {
            "new": "For new appointments, use the YourHealthFile patient portal.",
            "availability": (
                "For available appointments, check YourHealthFile directly. "
                "I cannot check live availability. Office staff can review a message "
                "through an approved intake channel."
            ),
            "reschedule": "Ask office staff to review your rescheduling request.",
            "cancel": "Ask office staff to review your cancellation request.",
        },
        "es": {
            "new": "Para citas nuevas, utilice el portal de pacientes YourHealthFile.",
            "availability": (
                "Consulte los horarios directamente en YourHealthFile. "
                "No puedo verificar la disponibilidad en tiempo real."
            ),
            "reschedule": "Solicite al personal que revise su cambio de cita.",
            "cancel": "Solicite al personal que revise su cancelación.",
        },
    }
    return {
        "success": True,
        "request_type": request_type,
        "language": language,
        "portal_name": "YourHealthFile",
        "new_patient_booking_url": BOOKING_URL,
        "practice_short_link": SHORT_BOOKING_URL,
        "short_link_redirect_verified": False,
        "instructions": instructions[language][request_type],
        "live_availability_checked": False,
        "appointment_booked": False,
        "appointment_changed": False,
        "appointment_cancelled": False,
        "message_submitted": False,
    }


def administrative_guidance(request_type: str, language: str = "en") -> dict:
    """Return an intake policy, not an assertion of submitted patient data."""
    if request_type not in REQUEST_TYPES:
        raise ValueError("Unknown administrative request type")
    if language not in {"en", "es"}:
        raise ValueError("Unsupported language")
    days = 2 if request_type == "outgoing_referral" else 3
    if language == "es":
        days_words = "dos" if days == 2 else "tres"
        text = (
            f"Permita hasta {days_words} días hábiles para el trámite rutinario. "
            "Algunos documentos requieren verificación o autorización. "
            "Las solicitudes urgentes deben revisarse por el personal."
        )
    else:
        text = (
            f"Please allow up to {days} business days for routine administrative processing. "
            "Medical records or faxes may require verification or authorization. "
            "Escalate urgent requests to staff. This is a target, not a guaranteed release deadline."
        )
    return {
        "success": True,
        "request_type": request_type,
        "language": language,
        "routine_processing_target_business_days": days,
        "processing_notice": text,
        "secure_intake_enabled": False,
        "message_submitted": False,
        "records_released": False,
        "fax_sent": False,
        "requires_authorized_staff_review": True,
    }
