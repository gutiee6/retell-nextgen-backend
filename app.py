"""Retell backend: verified webhook and public, non-PHI call guidance only."""
import json
import os
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from retell import Retell

from office_policy import (
    PRACTICE, OFFICE_ADDRESS, OFFICE_LOCATION_NOTE, OFFICE_PHONE, OFFICE_EMAIL,
    appointment_guidance, administrative_guidance, phone_status,
)

app = FastAPI(title="Retell office assistant backend", docs_url=None, redoc_url=None)
MAX_WEBHOOK_BYTES = 100_000
MAX_FUNCTION_BYTES = 4_096


@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "mode": "configuration_only"}


@app.post("/retell/webhook")
async def webhook(request: Request):
    key = os.getenv("RETELL_API_KEY", "")
    signature = request.headers.get("x-retell-signature", "")
    if not key or not signature:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if int(request.headers.get("content-length", "0") or "0") > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")
    try:
        verified = Retell(api_key=key).verify(
            raw.decode("utf-8"), api_key=key, signature=signature
        )
    except (ValueError, UnicodeDecodeError, TypeError):
        verified = False
    if not verified:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Never log, store, forward or include caller details in GitHub.
    return Response(status_code=204)


def _authorize(request: Request):
    token = os.getenv("FUNCTION_BEARER_TOKEN", "")
    auth = request.headers.get("authorization", "")
    if not token or not secrets.compare_digest(auth, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _public_args(request: Request, allowed: set[str]) -> dict:
    """Reject unexpected fields so Retell cannot send PHI to public-info tools."""
    if int(request.headers.get("content-length", "0") or "0") > MAX_FUNCTION_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")
    raw = await request.body()
    if len(raw) > MAX_FUNCTION_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=422, detail="Invalid JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Unexpected function arguments")
    # Retell may send parameters under "args" unless "Payload: Args Only" is enabled.
    if "args" in payload:
        if not set(payload).issubset({"args", "name"}) or not isinstance(payload["args"], dict):
            raise HTTPException(status_code=422, detail="Unexpected function envelope")
        if "name" in payload and (not isinstance(payload["name"], str) or len(payload["name"]) > 64):
            raise HTTPException(status_code=422, detail="Invalid function name")
        payload = payload["args"]
    if not set(payload).issubset(allowed):
        raise HTTPException(status_code=422, detail="Unexpected function arguments")
    if any(not isinstance(value, str) or len(value) > 40 for value in payload.values()):
        raise HTTPException(status_code=422, detail="Invalid argument value")
    return payload


@app.post("/retell/functions/office-routing")
async def office_routing(request: Request):
    _authorize(request)
    await _public_args(request, set())
    current = phone_status()
    return {
        "practice": PRACTICE,
        "office_address": OFFICE_ADDRESS,
        "shared_office_note": OFFICE_LOCATION_NOTE,
        "office_phone": OFFICE_PHONE,
        "office_email": OFFICE_EMAIL,
        "office_hours": current["phone_hours"],
        "phone_status": current,
        "departments": [
            {"name": name, "transfer_performed": False}
            for name in (
                "surgery_scheduling", "medical_records_referrals", "tms",
                "appointments", "office_staff", "urgent_postop",
            )
        ],
        "urgent_postop_action": "Invoke approved Retell transfer_urgent_postop node; this API does not transfer calls.",
        "clinical_policy": "Do not triage, diagnose, prescribe, or promise a callback. For medical emergencies, call 911.",
    }


@app.post("/retell/functions/appointment-info")
async def appointment_info(request: Request):
    """Useful even if another appointment tool cannot reach its upstream service."""
    _authorize(request)
    data = await _public_args(request, {"request_type", "language"})
    try:
        return appointment_guidance(data.get("request_type", "new"),
                                    data.get("language", "en"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/retell/functions/request-guidance")
async def request_guidance(request: Request):
    """Generic request instructions; never accepts/stores caller details."""
    _authorize(request)
    data = await _public_args(request, {"request_type", "language"})
    try:
        return administrative_guidance(data.get("request_type", "other"),
                                       data.get("language", "en"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/retell/functions/submit-message")
async def submit_message_disabled(request: Request):
    """Fail closed: a secure, approved message-delivery destination does not exist."""
    _authorize(request)
    await _public_args(request, set())
    return {
        "success": False,
        "status": "not_configured",
        "message_submitted": False,
        "instruction": (
            "Do not tell the caller a message was delivered. "
            "Use a practice-approved alternative intake channel."
        ),
    }
