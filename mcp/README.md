# Nevada Brain & Spine Care — read-only MCP for Retell AI

**Status: proposed implementation, not deployed, not clinically approved, and not connected to NextGen.** This is a separate service from the existing Retell webhook backend.

## What it does

Four MCP tools expose only public, non-patient-specific information:

| Tool | Purpose |
| --- | --- |
| `get_office_information` | Practice name, YourHealthFile link, English/Spanish instructions |
| `get_appointment_guidance` | Instructions for new, availability, change, and cancel requests; **no actual scheduling** |
| `get_department_routing` | Names office, surgery, records, TMS, or appointments category; **does not transfer callers** |
| `get_integration_status` | Truthfully reports lack of EHR, live calendar, call analytics, SMS, or patient data access |

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

1. Review and merge this PR only after confirming the feature is desired. Existing `app.py` and Retell endpoints are unchanged.
2. Create a **separate** approved web service (e.g. via Render if the practice's contracts permit) pointing to this repository. Use repository root as build context and `mcp/Dockerfile` as Dockerfile path, port `8080`.
3. In the host secret manager set `MCP_BEARER_TOKEN` to a unique random 32+ character value. Never place it in a Git commit, Retell prompt, URL query string, or chat.
4. After obtaining a stable HTTPS hostname, connect Retell AI agent → **Add MCP** → URL `https://YOUR-MCP-HOST/mcp` → HTTP header `Authorization: Bearer YOUR_MCP_BEARER_TOKEN`.
5. Select the four available tools and instruct the agent to call the relevant tool. Test English, Spanish, new appointment, cancellation, failure, and 401 handling using **synthetic callers only**.
6. Ensure YourHealthFile scheduling and SMS delivery are configured *separately*. Neither exists here.

## Safety controls and remaining work

- Only read-only public office information; no PHI is needed or retained. The server does not process webhook payloads, transcripts, clinical requests, or patient identifiers.
- All MCP requests require the separate bearer token; the health endpoint is public. Traffic must use HTTPS in deployment.
- It does not access NextGen OAuth, send texts, operate phones, schedule/cancel appointments, or access call logs.
- Current office phone hours are deliberately unspecified until confirmed by the practice.
- For emergencies, use the practice-approved emergency language and instruct callers to dial 911; never offer medical triage via MCP.
- Before any patient-specific integration, complete practice authorization, signed vendor BAAs, HIPAA risk assessment, least-privilege access controls, audit logging, encryption, retention rules, and an explicit approved workflow. **Do not assume Retell, Render, GitHub or this server is HIPAA compliant by default.**
- The existing repository is **public**. Never commit API credentials, PHI, transcripts, access tokens, real phone numbers, or appointment details.
