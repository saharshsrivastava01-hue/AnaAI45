# NEXUS Connect AI — launch checklist

This repository contains the NEXUS Connect AI backend, web dashboard, custom GPT Action definition, and a local interview-practice page.

## Current verified state
- The virtual interview practice page is committed at `nexus-connect-android/web/interview-assistant.html`.
- The Render Blueprint exists in the connected Render workspace.
- The first Render sync has **not** been approved: Render requires the secret `OPENAI_API_KEY`.
- No public API URL, live AI service, client calls, messages, or client projects are confirmed by this repository state.

## 1. Add the OpenAI API key securely
1. Create or retrieve an API key from the OpenAI developer platform.
2. In Render, open the NEXUS Connect AI Blueprint review page:
   https://dashboard.render.com/blueprint/exs-dc4thvgu01pc73fbhbmg/sync/exe-dc4thvou01pc73fbhchg
3. Approve the reviewed Blueprint only after you have added the required `OPENAI_API_KEY` value through Render's secure environment-variable flow.
4. Do not paste the secret into GitHub files, source code, chat messages, or this README.
5. Check the deployment logs and confirm the `/health` endpoint before connecting any client-facing integration.

The OpenAI API is billed separately from a ChatGPT subscription. Review the current API pricing and set a budget limit before enabling AI requests.

## 2. Configure the custom GPT Action
After the backend is deployed:
1. Copy the public HTTPS backend URL from Render.
2. Update the server URL in `nexus-connect-android/chatgpt-action/openapi.yaml` to that exact URL.
3. Create or edit a custom GPT in a ChatGPT plan/workspace that supports Actions.
4. Import the OpenAPI schema and configure Bearer authentication using the same `APP_ACCESS_TOKEN` value stored in Render.
5. Test only with non-sensitive sample data first.

A custom GPT Action is a separately configured integration. This repository does not automatically embed or modify the default ChatGPT application.

## 3. Interview assistant
Open `nexus-connect-android/web/interview-assistant.html` from the repository to inspect the standalone practice page. It supports question practice and a self-review rubric in the browser. It does not record or transmit microphone audio. You can use your phone keyboard's built-in dictation to enter an answer.

## 4. Important production limitations
- The current Render blueprint uses JSON file persistence. A free web service's local filesystem may be ephemeral; do not rely on it for durable lead or application records. Configure durable storage or a managed database before production use.
- Set `CORS_ORIGINS` to the exact trusted frontend origin before deployment.
- Keep `APP_ACCESS_TOKEN` and `OPENAI_API_KEY` secret.
- Review consent, privacy, retention, and outreach compliance before collecting personal information.
- NEXUS must not place calls, send emails, submit applications, or commit to client work without explicit user approval and a supported integration.

## 5. Current human approval boundary
The system can prepare interview practice, lead notes, proposals, and job-application drafts. Treat all external communication and commitments as drafts until a human explicitly reviews and approves them.
