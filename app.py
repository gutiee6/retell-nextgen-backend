"""Retell AI integration starter. No patient data storage or EHR access."""
import os
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from retell import Retell

app = FastAPI(title="Retell office assistant backend", docs_url=None, redoc_url=None)


async def read_limited_body(request: Request, max_bytes: int) -> bytes:
    """Read a request body without buffering more than the configured limit."""
    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        try:
            declared_size = int(declared_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc
        if declared_size < 0:
            raise HTTPException(status_code=400, detail="Invalid Content-Length")
        if declared_size > max_bytes:
            raise HTTPException(status_code=413, detail="Payload too large")

    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=413, detail="Payload too large")
        chunks.append(chunk)
    return b"".join(chunks)


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

    raw = await read_limited_body(request, 100_000)
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

    # Bound streamed requests too; Content-Length alone can be absent or misleading.
    await read_limited_body(request, 10_000)
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
