# SparkLoop AI API

A server-side Node.js API for the SparkLoop AI content studio.

## Capabilities
- OpenAI Responses API generation for content, seven-day campaigns, multi-platform repurposing, carousels, stories, storyboards, ad-copy drafts, SEO briefs and hook labs.
- Selectable public flagship text-model allowlist: GPT-6.2 Astra, GPT-6.2 Sol, GPT-6 Astra, GPT-6.1 Sol, GPT-6.1 Terra and GPT-6 Luna.
- Request-size limits, per-IP rate window and a low default process-wide daily request cap.
- Optional Postgres usage-event logging. No user accounts or cross-device storage are active in this prototype.
- The server does not store the prompt text or generated content. Responses API requests use `store: false`.

## Model pricing shown in the selector
Standard global USD list rates per 1 million text tokens (input / output): GPT-6.2 Astra $8 / $40; GPT-6.2 Sol $2 / $10; GPT-6 Astra $10 / $50; GPT-6.1 Sol $2 / $10; GPT-6.1 Terra $1 / $5; GPT-6 Luna $0.10 / $0.50. Rates can change and processing tiers, caching, regions and other features may change charges. The API returns an estimate from input/output token usage; it is not a final invoice.

## Run locally
1. Copy `.env.example` to `.env`.
2. Set `OPENAI_API_KEY` as a server-only secret.
3. Run `npm install`, then `npm start`.
4. Open `GET /health` to inspect API configuration and available models.

## Render setup
- Root directory: repository root.
- Build command: `cd sparkloop-ai-api && npm install`
- Start command: `cd sparkloop-ai-api && npm start`
- Set `APP_ORIGIN` to the exact frontend origin, including `https://`.
- Set `OPENAI_API_KEY` through Render Environment settings. Never commit it or place it in frontend code.
- Optional `DATABASE_URL` must point to a database dedicated to SparkLoop AI. Do not reuse another application's database.
- Default model: `gpt-6.2-sol`; model requests may select any model in the server allowlist.
- Keep `MAX_DAILY_REQUESTS` low and `MAX_DAILY_ESTIMATED_COST_USD` conservative until real user authentication, persistent quotas and budget alerts are implemented.
- The API returns model input/output token counts and an estimated USD token cost based on the standard public rate card; actual invoices may differ due to processing tier, cached tokens, model availability and other charges.

## Important limits
This is a beta, not a hosted ChatGPT account or model-weight copy. API token usage is billed separately by OpenAI. The model selector exposes a small set of current general-purpose text models rather than every specialised or ChatGPT-only model. Do not set an unlimited public usage budget.

No guaranteed virality, Google rank, revenue or reach. No automatic posting or advertising spend. Payment processing, accounts, withdrawals and UPI are not enabled.