# NextGen Office to SMS — controlled integration plan

**Implementation status: safe preview only, no live sending and no NextGen access.**
The linked YourHealthFile provider page is a patient-facing website, **not** an authenticated practice-level scheduling feed. Do not scrape or automate patient portal logins.

## What this change implements
- `POST /nextgen/sms/preview` with an independent administrator Bearer token.
- Strict request schema for synthetic test data only; rejects phone numbers, names and other extra fields.
- Neutral appointment scheduled/rescheduled/cancelled/reminder message templates, in Las Vegas local time.
- Requires affirmative SMS consent, enforces opt-out in preview logic.
- **No phone data accepted, no messages sent, no storage, and no appointment changes in NextGen.**

## Configuration in Render (preview only)
- `NEXTGEN_SMS_PREVIEW_TOKEN`: a new, long, unique random secret. Do not reuse Retell tokens.
- This feature has no dependency on or access to the Retell integration.
- Do not add patient information to test requests. Before *any* PHI passes through Render, ensure the **workspace itself** is HIPAA-enabled with a completed BAA and appropriate application controls.

Example **synthetic** request:
```bash
curl -X POST https://YOUR-APP.example/nextgen/sms/preview \
  -H "Authorization: Bearer YOUR_PREVIEW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"rescheduled","start_at":"2026-11-03T10:30:00-08:00","consent_verified":true,"opted_out":false}'
```

## To make it an actual NextGen → Twilio automated service
1. Ask **NextGen Office support** (not just the YourHealthFile patient portal) for an approved *practice-level*, supported appointment/schedule data interface or export, including change/cancellation events, API scope, rate limits, authentication, and appointment identifier. Public FHIR patient-access documentation does **not** guarantee appointment book access.
2. Verify practice authorization and production agreements. Render requires a HIPAA-enabled Scale/Enterprise workspace and signed BAA; Twilio HIPAA messaging also requires its eligible account/BAA. Check Retell independently if using call data. Configure no live data until this is verified.
3. Build an approved adapter to retrieve changes from NextGen. Never put NextGen credentials, exported schedules, patient phone numbers, or personal health information into the public GitHub repository or GitHub Actions.
4. Map NextGen appointment IDs, change status, approved phone, communication consent, and time zone. Use an approved encrypted database and a transactional outbox/deduplication key to prevent duplicate texts across retries, including after Render restarts. **Do not use the container filesystem for persistent patient data.**
5. Configure Twilio Messaging Service, A2P registration where applicable, delivery status processing, STOP/START opt-out handling, and a least-privilege sending credential. Send minimum-necessary messages; check practice policy about identifying the practice by name.
6. Add workflow tests for new, changed, canceled appointments, timezone/DST, opt-outs, consent revoked, duplicate events, retries and provider outages. Verify no PHI reaches server logs or telemetry.
7. Require an explicit production enablement step and staff-approved test plan. Retell remains separate from scheduling; an AI phone agent must not promise a confirmed booking unless NextGen accepts and confirms the update.

## Easier alternative
NextGen Office advertises native appointment reminders and patient engagement tools. Check whether these are enabled for the practice before buying/building a second messaging workflow.

Sources:
- NextGen Office APIs: https://www.nextgen.com/api
- NextGen Office patient engagement: https://www.nextgen.com/solutions/electronic-health-records/small-practices-nextgen-office
- Render HIPAA requirements: https://render.com/docs/hipaa-compliance
- Twilio HIPAA account requirements: https://www.twilio.com/docs/iam/twilio-editions/hippa
- Twilio consent: https://www.twilio.com/en-us/legal/messaging-policy
