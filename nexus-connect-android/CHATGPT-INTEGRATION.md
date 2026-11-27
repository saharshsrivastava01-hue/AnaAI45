# Connect NEXUS Connect AI to ChatGPT

## What this integration does
This OpenAPI document describes ChatGPT Custom GPT Actions for the NEXUS backend:
- Check backend health
- Generate AI-assisted drafts through the server-side OpenAI API
- Save and list user-provided leads
- Save, list, update, and delete job opportunity records
- Validate and order workflow plans

It does **not** provide autonomous job applications, outbound client calls, WhatsApp/email sending, payment collection, or background execution.

## Required deployment steps
1. Deploy the `backend/` folder to a public HTTPS Node.js host.
2. Configure server environment secrets: `APP_ACCESS_TOKEN` and `OPENAI_API_KEY`. Optionally set `OPENAI_MODEL`, `NEXUS_LEADS_FILE`, and `NEXUS_APPLICATIONS_FILE`.
3. Keep the token and OpenAI key private. Never paste them into this repository or Android app.
4. Replace `https://YOUR_PUBLIC_BACKEND_HOST` in `chatgpt-actions.openapi.yaml` with the real HTTPS base URL.
5. Verify `GET /health` returns JSON over HTTPS.
6. In ChatGPT, open GPT creation/editing, go to Configure, find Actions, choose Create new action, and paste the OpenAPI YAML.
7. Configure Authentication as API Key, choose Bearer, and enter the same `APP_ACCESS_TOKEN` configured on the backend. Save the GPT and test read-only health first.

## Suggested GPT instructions
You are NEXUS Connect AI, an assistant that helps Saharsh prepare truthful WordPress/web-design proposals, organize prospect records, and track job opportunities. Use actions only for the specific task the user requests. Never claim a lead was contacted, a job application submitted, an interview booked, money earned, or a client acquired unless a separate verified result confirms it. Drafts and records are not external submissions. Ask for explicit confirmation before any future action that communicates externally, spends money, accepts terms, or makes commitments. Do not fabricate the user's skills, portfolio, experience, or credentials.

## Security and readiness notes
- The OpenAPI server URL is intentionally a placeholder until deployment.
- The backend currently uses a shared bearer token. Use a strong random token and rotate it if exposed.
- Configure rate limiting, HTTPS, persistent production database storage, backups, and monitoring before real customer data is used.
- The backend must be reachable from ChatGPT's servers; localhost URLs will not work.
- ChatGPT plan/workspace access and Custom GPT Action availability depend on the user's account and current product settings.
- This integration file has not yet been imported into a GPT or tested against a deployed backend.
