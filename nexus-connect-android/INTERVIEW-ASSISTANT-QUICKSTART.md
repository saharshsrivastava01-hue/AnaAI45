# NEXUS Virtual Interview Assistant — Quick Start

## What is ready

The standalone browser-based interview practice page is:

`web/interview-assistant.html`

Open it directly in a browser, or serve the `web` directory with any static file server. It does not require an API key and does not transmit answers anywhere. On Android, open the page in Chrome and use the keyboard microphone button for speech-to-text dictation if your keyboard supports it.

## Practice flow

1. Enter the target role and choose the interview focus.
2. Start a mock interview.
3. Type an answer or use device keyboard dictation.
4. Select **Review this answer** for a four-point self-review.
5. Move to the next question.

The review is a practice aid, not an employer score or a guarantee of interview performance.

## Connect it to ChatGPT

A separate custom GPT Action definition is in `chatgpt-action/openapi.yaml`, with setup notes in `chatgpt-action/README.md`. This is not automatically embedded in the standard ChatGPT app. It requires a publicly reachable HTTPS backend, a custom GPT with Actions enabled for the user's plan, and a bearer token configured on both sides.

## Backend deployment prerequisites

- Review `render.yaml` and the Render Blueprint before applying it.
- Set `OPENAI_API_KEY` as a secret in the Render service's Environment page. Do not commit it or paste it into source control.
- Set `APP_ACCESS_TOKEN` to a long random secret (the blueprint may generate this).
- Set `CORS_ORIGINS` to the exact trusted frontend origin(s); remove the placeholder before use.
- Configure durable storage before relying on lead/application records. The current JSON-file storage may be lost when an ephemeral service restarts or redeploys; use a persistent disk or database for production.
- Run backend tests and verify `/health` before sharing the endpoint.

## Important boundaries

NEXUS does not place calls, send emails, submit job applications, make payments, or accept client projects automatically. Use it to prepare work for human review. Do not claim a project is confirmed until the client has explicitly agreed to scope, price, and timeline.
