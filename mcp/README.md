# Nevada Brain & Spine Care — read-only MCP for Retell AI

**Status: deployed on Render as a read-only public-information MCP service; not automatically connected to the live Retell agent, not connected to NextGen, and not approved to process patient information.** This is a separate service from the Retell webhook backend.

## What it does

Six MCP tools expose only public, non-patient-specific information:

| Tool | Purpose |
| --- | --- |
| `get_office_information` | Practice name, YourHealthFile link, English/Spanish instructions |
| `get_appointment_guidance` | Instructions for new, availability, change, and cancel requests; **no actual scheduling** |
| `get_department_routing` | Names office, surgery, records, TMS, or appointments category; **does not transfer callers** |
| `get_integration_status` | Truthfully reports lack of EHR, live calendar, call analytics, SMS, and patient data access |
| `get_phone_hours_status` | Calculates Pacific time against the **proposed** M–F 7–11 AM staff window, separates Friday clinic hours; does not verify actual staff presence |
| `get_administrative_request_guidance` | Medical records, faxes, forms, refills, referral requests: **3 business days** routinely; **outgoing referrals: 2 business days**; no submission or release |

The approved new-patient link is:

https://www.yourhealthfile.com/providers/1289988/las-vegas-neurological-surgery-doctor.html

**Important:** The MCP server does not verify whether the portal itself is operational or whether specific appointment slots exist.

## Local test (synthetic data only)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r mcp/requirements.txt
PYTHONPATH=mcp python -m unittest discover -s mcp/tests -v

# Generate a separate random secret and export it locally.
# Do not use the Retell API key as MCP_BEARER_TOKEN.
export MCP_BEARER_TOKEN=replace-with-a-unique-random-32-plus-character-secret
uvicorn office_mcp:app --app-dir mcp --host 127.0.0.1 --port 8001
```

GET http://127.0.0.1:8001/health should return `status: ok`.
POST http://127.0.0.1:8001/mcp without a valid `Authorization: Bearer ...` header returns HTTP 401.
An MCP client must supply that header to initialize, discover, and call tools.

## Deployment

The existing Render service is **`retell-nextgen-backend`**, hosted at `https://retell-nextgen-backend.onrender.com`, with Dockerfile `mcp/Dockerfile`. GitHub changes to `main` auto-deploy there. These changes only extend read-only tool responses; no patient data is accepted.

1. Review and merge this PR after tests pass. Existing `app.py` REST guidance and separate phone webhook services are unchanged.
2. Keep the existing Render service's `mcp/Dockerfile` and its configured port. No additional service is necessary.
3. In the host secret manager set `MCP_BEARER_TOKEN` to a unique random 32+ character value. Never place it in a Git commit, Retell prompt, URL query string, or chat.
4. After obtaining a stable HTTPS hostname, connect Retell AI agent → **Add MCP** → URL `https://YOUR-MCP-HOST/mcp` → HTTP header `Authorization: Bearer YOUR_MCP_BEARER_TOKEN`.
5. Select the six available tools and instruct the agent to call the relevant tool. Test English, Spanish, new appointment, cancellation, failure, and 401 handling using **synthetic callers only**.
6. Ensure YourHealthFile scheduling and SMS delivery are configured *separately*. Neither exists here.

## Safety controls and remaining work

- Only read-only public office information; no PHI is needed or retained. The server does not process webhook payloads, transcripts, clinical requests, or patient identifiers.
- All MCP requests require the separate bearer token; the health endpoint is public. Traffic must use HTTPS in deployment.
- It does not access NextGen OAuth, send texts, operate phones, schedule/cancel appointments, or access call logs.
- The policy currently contains **proposed** staffed phone hours, Monday–Friday 7:00 AM until before 11:00 AM Pacific. Exactly 11 AM is outside the window. The physical Friday clinic 7 AM–noon does not extend telephone coverage. Practice approval is still required, and the MCP server cannot independently confirm a staff member is on duty.
- The office address and shared Dr. Forte location are read from the repository's existing public office policy and require staff verification before public announcement.
- For emergencies, use the practice-approved emergency language and instruct callers to dial 911; never offer medical triage via MCP.
- Before any patient-specific integration, complete practice authorization, signed vendor BAAs, HIPAA risk assessment, least-privilege access controls, audit logging, encryption, retention rules, and an explicit approved workflow. **Do not assume Retell, Render, GitHub or this server is HIPAA compliant by default.**
- The existing repository is **public**. Never commit API credentials, PHI, transcripts, access tokens, real phone numbers, or appointment details.

## Tool setup and failure handling

- In the Retell agent, use `get_appointment_guidance` for scheduling questions and explicitly say **YourHealthFile** even if the tool fails. This tool cannot book or check live availability.
- Use `get_phone_hours_status` for Pacific-time coverage windows, but **never claim real staff are on duty** from its schedule alone. Confirm official hours with office leadership.
- Use `get_administrative_request_guidance` for routine records, fax, referral, forms, refill, and dose-change policies. **It does not collect or submit patient requests.** No names, DOBs, medications or medical details belong in tool arguments.
- Urgent postoperative calls still need the real Retell `transfer_urgent_postop` action. `get_department_routing` is *not* a transfer.
- Never claim a message, record release, fax or prescription was processed without an independently verified response from an approved secure workflow.
