# Deployment guide (draft; not approved for patient calls)

This repository now has a Dockerfile so it can run on a managed container host. A suitable candidate is AWS App Runner, subject to approval by the practice's administrator/privacy lead.

## Before creating a live service

- The practice must own or authorize the AWS account and approve all charges and access.
- Execute the required AWS BAA and verify App Runner and every supporting service used are in the current HIPAA-eligible scope. AWS compliance status does not by itself make this application compliant.
- Execute the required Retell BAA before sending protected health information to Retell.
- Complete practice review of call recording/transcripts, data retention, access controls, audit logging, incident response, transfer destinations, emergency instructions, and the agent's approved script.
- This scaffold has no EHR access or scheduling integration. Its webhook only verifies a Retell signature and returns 204; the routing function returns generic static metadata. It is not ready to handle patient call content.

## Candidate deployment steps

1. In an authorized AWS account, create an App Runner service from this GitHub repository and select the `codex/prepare-container-hosting` branch for review or `main` after the changes are approved.
2. Configure a source build from the repository's `Dockerfile`, use container port `8080`, and set the health check path to `/health`.
3. Configure `RETELL_API_KEY` and `FUNCTION_BEARER_TOKEN` through the hosting provider's secret manager. Do not put either value in GitHub, this file, an issue, or chat.
4. Confirm the service provides a public HTTPS URL and that `GET /health` returns `{"status":"ok","mode":"configuration_only"}`.
5. Only after practice approval, configure a Retell webhook to `https://YOUR-HOST/retell/webhook`. The endpoint currently discards verified events; it does not create call summaries or tasks.
6. Use synthetic test calls to verify webhook delivery and agent transfers. Transfers are configured in Retell's agent flow, not by this backend.
7. Keep real patient data out until the practice completes the required security and privacy review and explicitly approves the workflow.

## GitHub deployment automation

GitHub Actions can run tests and trigger a deployment to an approved host. The repository currently only runs offline tests; this branch does not create a host, configure cloud credentials, or deploy automatically. Add deployment credentials using a short-lived, least-privilege identity after the practice approves the cloud account and deployment design.
