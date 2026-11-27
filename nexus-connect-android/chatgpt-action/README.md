# Connect NEXUS to a custom GPT

This folder contains a starter OpenAPI schema and GPT instructions for connecting NEXUS Connect AI to ChatGPT using a custom GPT Action.

## Important
This does not automatically install a GPT into the user's ChatGPT account. The backend must first be deployed to a public HTTPS host, then the user must create/configure a GPT and add the Action schema. The current repository is source code, not a live deployed service.

## Setup
1. Deploy `backend/` to a trusted HTTPS host.
2. Configure server secrets: `APP_ACCESS_TOKEN`, and optionally `OPENAI_API_KEY` for the backend's AI drafting feature. Keep all secrets server-side.
3. Set `NEXUS_APPLICATIONS_FILE` and `NEXUS_LEADS_FILE` to durable storage paths. JSON files are suitable only for a single-instance prototype; use a managed database before multi-user production.
4. In the OpenAPI file, replace `https://YOUR-DEPLOYED-HOST` with the deployed HTTPS origin.
5. In ChatGPT, create a custom GPT, open its Actions configuration, import `openapi.yaml`, and configure Authentication as API Key / Bearer. Paste the same `APP_ACCESS_TOKEN` value as the bearer token.
6. Add the text from `GPT-INSTRUCTIONS.md` to the GPT's Instructions.
7. Test `checkBackend`, then a harmless lead/application list action. Do not enable any external action that sends messages or places calls.

## Current limitations
- This Action provides API access for drafts, saved leads, job tracker records, and workflow validation.
- It does not integrate into the default ChatGPT assistant automatically; it is a custom GPT Action configuration.
- It does not create a live voice agent, place calls, send emails, submit applications, or deploy websites.
- The OpenAPI server URL is intentionally a placeholder until the backend is actually deployed.
