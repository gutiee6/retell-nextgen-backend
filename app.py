"""Retell AI integration starter. No patient data storage or EHR access."""
import os
import secrets
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from retell import Retell

app = FastAPI(title="Retell office assistant backend", docs_url=None, redoc_url=None)

# These routes must be protected; no patient-specific workflows are implemented.
@app.get("/health")
def health():
    return {"status": "ok", "mode": "configuration_only"}

@app.post("/retell/webhook")
async def webhook(request: Request):
    api_key = os.getenv("RETELL_API_KEY", "")
    signature = request.headers.get("x-retell-signature", "")
    if not api_key or not signature:
        raise HTTPException(status_code=401, detail="Unauthorized")
    raw = await request.body()
    if len(raw) > 100_000:
        raise HTTPException(status_code=413, detail="Payload too large")
    try:
        verified = Retell(api_key=api_key).verify(
            raw.decode("utf-8"), api_key=api_key, signature=signature
        )
    except (ValueError, UnicodeDecodeError, TypeError):
        verified = False
    if not verified:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Deliberately do not log, store, or forward call payloads/transcripts/phone numbers.
    return Response(status_code=204)

@app.post("/retell/functions/office-routing")
async def office_routing(request: Request):
    """Static generic office information; no patient details accepted or retained."""
    token = os.getenv("FUNCTION_BEARER_TOKEN", "")
    auth = request.headers.get("authorization", "")
    if not token or not secrets.compare_digest(auth, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Never log request body; do not process PHI.
    if int(request.headers.get("content-length", "0") or "0") > 10_000:
        raise HTTPException(status_code=413, detail="Payload too large")
    return {
        "practice": "Nevada Brain & Spine Care",
        "office_hours": "Not confirmed; transfer to staff for current hours.",
        "departments": [
            {"name": "surgery_scheduling", "transfer": "Use Retell approved transfer node"},
            {"name": "medical_records_referrals", "transfer": "Use Retell approved transfer node"},
            {"name": "tms", "transfer": "Use Retell approved transfer node"},
            {"name": "appointments", "transfer": "Use Retell approved transfer node"},
            {"name": "office_staff", "transfer": "Use Retell approved transfer node"}
        ],
        "clinical_policy": "Do not triage, diagnose, prescribe, or promise a callback or appointment. For immediate medical emergencies, instruct caller to call 911."
    }
