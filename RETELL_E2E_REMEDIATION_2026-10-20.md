# 2026-10-20 Retell E2E failures — implementation / validation

## Observed (19 failures at 12:32 PM Pacific)
The agent did not invoke `send_office_message` in the success, failure, or timeout scenarios. It declined intake even when explicitly asked. Some hours and website tests also failed. GitHub's public REST/MCP service intentionally does NOT submit patient messages. Updating GitHub docs by itself does **not** update Retell's published agent or connect its custom functions.

## REQUIRED before enabling real patient calls

1. Verify the public office phone (702-763-7384), email, staffed phone hours (M–F 7:00 to BEFORE 11:00 AM Pacific), Friday in-person clinic (7 AM–noon), address, and intended YourHealthFile short-link redirect with practice leadership.
2. Review vendor BAAs, recording/transcripts, HIPAA risk assessment, hosting vendor, access control, retention, audit logging, staff access, incident response, data-flow design, and practice authorization. Do not assume a public Render web service can handle PHI.
3. Build or choose a **private, authenticated, approved staff intake receiver**, isolated from the current public read-only endpoint, that accepts only minimum-necessary, consented information; returns a confirmed durable receipt with a unique `message_id`; and implements idempotency. The currently deployed `/retell/functions/submit-message` is intentionally disabled and MUST NOT be used.
4. In Retell add the actual Custom Function named **`send_office_message`** pointing at that approved receiver. Its tool schema must match the supported intake fields; configure authentication, TLS, appropriate timeout handling, and verified success responses. **Do not make the endpoint unauthenticated to satisfy E2E tests.** Never include secrets or patient data in GitHub.
5. Configure a separate real Retell **`transfer_urgent_postop`** call transfer with a verified practice-approved destination and genuine failure reporting, not a routing-text function. Do not publish a private number in public code.
6. Confirm that the agent's **published version** has the correct V22 rules and tool declarations, rather than only a draft in the Retell editor. Test in a synthetic sandbox with fake names/numbers and configured tool mocks. Keep the live secure-intake gate FALSE until steps 1–5 are complete. An E2E mock is NOT a secure live receiver.

## Required tool outcome contract (the secure receiving system must implement this)

Success: `{"success":true,"status":"submitted","message_id":"<unique acknowledged ID>"}`.
Explicit failure: `{"success":false,"status":"failed"}`.
Unknown/timeout: `{"success":null,"status":"unknown"}` or a transport timeout.
Unavailable: `{"success":false,"status":"not_configured"}`.

Treat missing fields, HTTP timeouts, 5xx, connection closures, and unclear response status as **unknown** unless the receiver can *positively* confirm it rejected the message before persisting it. Do not retry automatically. Use a stable idempotency key per consented final revision/call, enforced at the approved receiver, to avoid duplicate messages.

## Mapping: the 19 failed test cases

| Test | Necessary Retell action / observable behavior |
| --- | --- |
| E2E: office message timeout | Attempt exactly one confirmed submission. On unknown timeout: "I cannot confirm whether your message was received." Do not declare failure or auto-retry. |
| E2E: after-hours message succeeds | Say staff unavailable due to phone hours, confirm name/DOB/number/reason in secure mode, call tool, and acknowledge only a verified receipt. |
| 02 - Friday clinic hours are not phone hours | Clinic 7 AM-noon is in person; live phones end before 11 AM; 11:30 Friday = outside phone window; offer *approved* message intake. |
| Website: spells address and repeats | Say YourHealthFile, give approved TinyURL, spell entire path character-by-character and repeat on request, no unsolicited SMS. |
| Records: submission fails | Collect requester/organization and callback + fax when relevant, read back, obtain confirmation, invoke tool; on actual failure do not claim sent. |
| Scheduling: cancellation | Take a *cancellation request* through secure tool; no cancelled appointment claim. |
| Postop: transfer fails, non-severe, callback message | Attempt actual approved transfer; say failed; offer secure urgent callback intake, not only a phone number. |
| 08 - Existing appointment change | Caller-reported Friday 9 AM; requested 10 AM; read back confirmed contact details and send *request*; no change claim. |
| 05 - Closing boundary at exactly 11 AM | 11:00 AM is outside phone coverage; offer secure intake, no live transfer guarantee. |
| E2E: live hours staff request | Say M–F 7–11 AM Pacific generally staffed; no guarantee someone answers; no fake transfer. |
| Scheduling: how to schedule | Explicitly refer to Dr. Nagy's YourHealthFile portal + approved and fully spelled TinyURL when requested; office must confirm. |
| Records: urgent clinical deadline flagged | Record "needed before surgery tomorrow" as time-sensitive; mark urgent staff review, not routine 3-day assurance. |
| 16 - Message delivery is uncertain | Unknown is neither success nor failure; one call only; contact alternative without callback promise. |
| Website: no other questions ends call | After website info ask once "Anything else?" then thank and use end_call when declined; no restart. |
| Scheduling: rescheduling | Read back proposed Friday morning request; send message; no reschedule claim. |
| 15 - Message submission fails | Invoke once after confirmation; on explicit failure say not submitted; offer phone/email with name and callback only, no medical details. |
| After-hours intake | Recognize outside-hours, obtain/confirm minimal identifiers in approved secure mode, invoke tool, await acknowledgment. |
| 03 - Before opening at 6:59 AM | 6:59 AM Pacific is closed. Do not say open or promise callback at 7:00. |
| Records: fax request to another facility | Collect organization/return number, verify receiving fax number digit-by-digit, confirm request, submit; state staff-review target up to 3 business days ONLY after confirmed receipt. Never claim fax sent. |

## Retell regression sequence

- In a separate synthetic test agent: ensure the custom tool named `send_office_message` is enabled and its mocks are injected in Retell's E2E run. Success, explicit failure and unknown/timeout must each be tested with otherwise identical readback and confirmation paths.
- Set the E2E simulated time via `{{current_time}}` in Pacific. Test Tuesday 6:59, 7:00, 10:59:59, 11:00 and Friday 11:30.
- Ensure caller corrections replace stale callback numbers; confirm final revisions before tool invocation.
- Check Retell call logs for actual tool invocation, arguments (synthetic only), return status, and whether the published agent version matches the prompt.
- Add four negative tests: general directions never request DOB, no message after caller declines, no retry on unknown delivery, and no PHI to the public `/retell/functions/*` endpoints.
- Only after synthetic tests pass and compliance/security checks are satisfied should the authorized practice administrator publish the live changes.

## What cannot be repaired by a GitHub push
GitHub cannot publish the Retell agent, register custom tools, provision an approved private message receiver, prove the TinyURL redirect, verify a phone transfer, or attest HIPAA compliance. The Render MCP `/mcp` service contains read-only office information; it must stay that way until a separate secure intake integration is approved.
