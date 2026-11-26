# SparkLoop AI API

Node 20+ API for the SparkLoop AI static frontend.

## Run locally
1. Copy `.env.example` to `.env`.
2. Set `OPENAI_API_KEY` as a server-only secret.
3. Run `npm install`, then `npm start`.
4. Open `GET /health` to inspect configuration.

## Render setup
- Root directory: repository root (commands below enter this folder).
- Build command: `cd sparkloop-ai-api && npm install`
- Start command: `cd sparkloop-ai-api && npm start`
- Set `APP_ORIGIN=https://sparkloop-ai.onrender.com`.
- Set `OPENAI_API_KEY` through Render Environment settings. Never commit it.
- Optional `DATABASE_URL` must point to a database dedicated to SparkLoop. Do not reuse another application's database.
- Set `OPENAI_MODEL=gpt-6.2-sol`; change to `gpt-6.2-astra` only after checking the account's budget.

## Notes
Without an API key the AI endpoint returns a clear 503. The browser can continue using its local draft fallback. Without a dedicated database, persistent accounts, cross-device drafts and wallet records are not available. The wallet is not implemented as money storage, and no UPI payment flow is enabled.
