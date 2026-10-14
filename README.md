# Nevada Brain & Spine Care — Retell AI backend (starter)

**Status: code scaffold only; no verified live NextGen connection or SMS sending. Retell deployment and compliance status must be checked separately.**

## Implemented
- `GET /health` status endpoint.
- `POST /retell/webhook` rejects unsigned requests and uses the official Retell SDK verifier. Valid webhook events return 204; no transcript, phone number, recording, call payload, or patient data is logged, saved or sent elsewhere.
- `POST /retell/functions/office-routing` requires a separate Bearer token; returns static, generic routing metadata only.
- No scheduling, text sending, NextGen writes, recording, or clinical triage.
- `GET /nextgen/sms/status` and token-protected `POST /nextgen/sms/preview` to generate **synthetic, offline, never-sent** appointment-message previews with consent checks. See [NEXTGEN_SMS_SETUP.md](NEXTGEN_SMS_SETUP.md).

## Running locally with **synthetic test calls only**
```bash
python -m venv .venv
pip install -r requirements.txt
# Set RETELL_API_KEY and FUNCTION_BEARER_TOKEN in local environment (never commit them)
uvicorn app:app --host 127.0.0.1 --port 8000
```

## Connect in Retell AI (after approval)
1. Verify vendor-specific HIPAA agreements for Retell, telecom provider, speech and hosting services. Review recording/transcript storage and retention before patient calls.
2. Deploy this application to an approved HTTPS hosting service; store secrets in the host's secret manager, not GitHub source. This GitHub repository is currently **public**; change to private before adding anything sensitive (never commit PHI even privately).
3. Add a Retell webhook pointing to `https://YOUR-HOST/retell/webhook`; set `RETELL_API_KEY` to the key approved for webhook verification. Do not enter any API key in a chat or code commit.
4. Create a Retell **Conversation Flow** agent with office info, surgery scheduling, records/referrals, TMS, appointments and staff transfer branches. Set transfers inside Retell to verified approved staff destinations. Test failed-transfer, no-input, Spanish, and after-hours cases using synthetic calls.
5. Optional: configure a Retell custom function `POST https://YOUR-HOST/retell/functions/office-routing` with an `Authorization: Bearer <FUNCTION_BEARER_TOKEN>` header. **This endpoint only supplies static routing information; it cannot actually transfer calls.** Transfers require Retell transfer nodes.
6. Add approved office hours, after-hours coverage and escalation policies in the agent knowledge base. Do not publish unverified hours or imply 24/7 live physician availability.
7. Do not connect NextGen EHR without written practice authorization, vendor approval, scoped OAuth, audit logging and HIPAA review. **No NextGen integration is implemented here.**

## GitHub automation
- GitHub Actions runs offline tests on pushes to `main`, pull requests, and manual runs.
- Tests use synthetic payloads and mock Retell verification; they do not call Twilio or Retell and do not contain patient data.
- Run locally with `python -m unittest discover -s tests -v`.

## Safety requirements
- Never send names, dates of birth, phone numbers, patient-specific requests, transcripts or recordings to GitHub Issues or Actions.
- Do not promise callbacks, clinical advice, prescriptions or confirmed appointments when no approved workflow exists.
- Real patient call data must not flow into this scaffold before risk assessment, BAAs, authentication, access controls, encryption, audit trails, and retention policy are implemented.
- Existing Google Voice or Twilio routing is **not** changed by this repository.
