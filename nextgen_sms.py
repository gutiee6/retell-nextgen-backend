"""Privacy-minimized, OFFLINE appointment SMS drafting. No NextGen or SMS network calls.

Never feed real patient data into an unapproved hosting environment.
"""
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

PRACTICE_NAME = "Nevada Brain & Spine Care"
LOCAL_TZ = ZoneInfo("America/Los_Angeles")


class AppointmentAction(str, Enum):
    scheduled = "scheduled"
    rescheduled = "rescheduled"
    cancelled = "cancelled"
    reminder = "reminder"


class SmsPreviewRequest(BaseModel):
    """Synthetic inputs only. PHI fields, including phone and patient name, forbidden."""

    model_config = ConfigDict(extra="forbid", strict=True)

    action: AppointmentAction
    start_at: datetime | None = None
    consent_verified: bool = False
    opted_out: bool = False

    @field_validator("start_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("start_at must contain an explicit UTC offset")
        return value


def preview_sms(payload: SmsPreviewRequest) -> str:
    """Generate a draft only; never send. Consent required even for preview."""

    if not payload.consent_verified or payload.opted_out:
        raise ValueError("Verified SMS consent is required and opt-outs must be honored.")

    if payload.action == AppointmentAction.cancelled:
        body = "Your appointment has been canceled. Please contact the office if you need help."
    else:
        if payload.start_at is None:
            raise ValueError("start_at is required for scheduled, rescheduled, or reminder.")
        local = payload.start_at.astimezone(LOCAL_TZ)
        # Do not include diagnosis, provider, procedure, or patient identity.
        formatted = local.strftime("%a, %b %-d at %-I:%M %p")
        if payload.action == AppointmentAction.scheduled:
            body = f"Your appointment is scheduled for {formatted}."
        elif payload.action == AppointmentAction.rescheduled:
            body = f"Your appointment has been moved to {formatted}."
        else:
            body = f"Reminder: your appointment is {formatted}."

    return f"{PRACTICE_NAME}: {body} Reply STOP to opt out."
