# Nevada Brain & Spine Care — Retell AI backend

**Status: review/staging scaffold only. Not automatically connected to Retell, Render, NextGen or live patient message intake. Not approved for patient calls.**

This branch improves the October 19 Retell evaluation's **public-information behavior** without collecting or transmitting patient data. The Python endpoints are stateless, require a separate function bearer token and do not deliver messages or connect calls.

## Public endpoints and capabilities

| Endpoint | Result | Does it perform the action? |
| --- | --- | --- |
| GET `/health` | Returns service status | Health check only |
| POST `/retell/webhook` | Verifies Retell signature, discards event | No storage or call actions |
| POST `/retell/functions/office-routing` | Phone-hours boundary and routing labels | No call transfer |
| POST `/retell/functions/appointment-info` | Canonical YourHealthFile link and type-specific fallback | No live availability/booking |
| POST `/retell/functions/request-guidance` | Routine 3-business-day policy for an administrative category | No patient intake or fax |
| POST `/retell/functions/submit-message` | `success: false`, `message_submitted: false` | **Disabled** until approved secure intake exists |

All `/retell/functions/*` endpoints require `Authorization: Bearer <FUNCTION_BEARER_TOKEN>`. Public-info endpoints reject any unexpected arguments rather than accepting patient details. The `submit-message` endpoint intentionally fails closed. Do not use these endpoints for names, phone numbers, dates of birth, prescriptions, symptoms, records or PHI.

### Retell custom function setup (manual)

- `office_routing` → POST `https://YOUR-HOST/retell/functions/office-routing`, empty JSON `{}`.
- `appointment_info` → POST `https://YOUR-HOST/retell/functions/appointment-info`. Optional JSON: `{"request_type":"new"}`. Allowed types: `new`, `availability`, `reschedule`, `cancel`.
- In Retell custom functions, **turn on Payload: Args Only** so Retell sends only function arguments. The default full payload contains a `call` object with transcripts, which this public-information backend intentionally rejects. Do not send caller metadata or PHI.
- `request_guidance` → POST `https://YOUR-HOST/retell/functions/request-guidance`. Example `{"request_type":"medical_records"}`. Other categories: `fax`, `referral`, `outgoing_referral`, `forms`, `billing`, `refill`, `dose_change`, `other`. Routine outgoing referrals have a separate two-business-day target; routine records, faxes, and forms have a three-business-day target.
- Avoid adding `submit-message` to a live agent until a real compliant intake destination is configured and approved.
- For the already-existing MCP `get_appointment_guidance` tool, the fixed YourHealthFile URL is also available; **select and connect the correct tool in Retell**. See `mcp/README.md`.
- **Actual** `transfer_urgent_postop` must be configured as a Retell transfer node/action with verified destination; this code cannot perform a phone transfer.
- Paste and review `agent-instructions.md` inside the Retell agent. GitHub edits do not update the agent prompt on their own.

The user's October 19 evaluation proposes live phone staffing **Wednesday and Thursday 10:00 AM up to but excluding 2:00 PM Pacific** and a separate **Friday 10:00 AM-2:00 PM in-person clinic**. `office_policy.py` implements that boundary, including DST, for automated tests. **These hours were provided by the practice on Oct 20, 2026.** The practice-confirmed address is **9488 West Flamingo Road, Suite 100, Las Vegas, NV 89147**, shared with Dr. Forte's family practice. The phone and hours in this draft reflect the practice details supplied Oct 20, 2026.

The new-patient URL recorded in the existing MCP documentation is (the office-provided short link `https://tinyurl.com/Dr-Nagy` has not been independently redirect-verified):

https://www.yourhealthfile.com/providers/1289988/las-vegas-neurological-surgery-doctor.html

## Testing
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Tests use only synthetic input and mocked Retell signature verification. GitHub Actions runs the same checks for pull requests.

## Security and deployment gates

1. The repository is **public**. Never commit API keys, access tokens, transcripts, phone numbers, patient identifiers, clinical data or message payloads.
2. The practice must authorize all vendors, hosting, access controls, BAAs, recording/transcript rules, audit logs, and retention before real calls or PHI are processed.
3. Store `RETELL_API_KEY` and `FUNCTION_BEARER_TOKEN` in an approved host secret manager, never in the repository.
4. Deploy to approved HTTPS hosting only after review. Do not attach a real patient phone line to this scaffold.
5. Separately implement and verify a secure request queue, message delivery acknowledgment, urgent-postop transfer, address, and scheduling/availability if desired. Do not claim any of these exist until verified.

Existing Twilio or Google Voice call forwarding is unchanged.
