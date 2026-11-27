# Connect NEXUS to ChatGPT

This repository now includes an OpenAPI schema and operating instructions for a Custom GPT Action. This does not modify ChatGPT itself or automatically publish a GPT.

## Prerequisites
1. Deploy the NEXUS backend to a public HTTPS host.
2. Configure `APP_ACCESS_TOKEN` as a strong server-side secret.
3. Configure `OPENAI_API_KEY` only on the backend if AI drafting is required. ChatGPT subscriptions do not include API credits.
4. Update the `servers[0].url` value in `openapi.yaml` to your real backend HTTPS URL.
5. Confirm CORS and backend security settings. GPT Actions call server-to-server; do not expose backend secrets in a browser.

## Configure a Custom GPT
1. In ChatGPT, open the GPT builder (if available on your plan) and create a GPT.
2. Add the text from `GPT-INSTRUCTIONS.md` to its Instructions.
3. Add an Action and import `openapi.yaml`.
4. Configure Authentication as API Key, Bearer, and enter the same `APP_ACCESS_TOKEN` configured on the backend.
5. Save and test only after the backend is deployed and the health endpoint responds.

## Current limitations
- No live backend host has been supplied or deployed, so the placeholder server URL must be replaced.
- This Action schema provides lead/job tracking and draft preparation only. It does not call prospects, send email/WhatsApp, submit job applications, accept payments, or execute workflows.
- The current JSON-file storage is suitable only for a small single-instance prototype, not production multi-user use.
- Review every AI-generated draft before use.
