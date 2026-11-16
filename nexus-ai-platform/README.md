# NEXUS Global Commerce — backend foundation

This folder adds a FastAPI backend to the existing static storefront. It is an early development foundation, not a finished production commerce service.

## Included
- Product catalogue API backed by SQLite.
- Order-intake API that calculates totals from server-side product prices.
- AI assistant endpoint using an OpenAI-compatible Chat Completions API.
- Token-protected product creation and admin summary endpoints.
- Health endpoint.

## Run locally
1. Install Python 3.10+.
2. Open a terminal in `nexus-ai-platform/backend`.
3. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set values in your shell or hosting provider. Do not commit real API keys.
5. Start the API:

   ```bash
   uvicorn main:app --reload
   ```

6. Open `http://127.0.0.1:8000/docs`.

## API routes
- `GET /health`
- `GET /api/products`
- `POST /api/products` — requires `X-Admin-Token`.
- `POST /api/orders` — records an order as `pending_payment`; it does not collect money.
- `POST /api/assistant` — requires a server-side `AI_API_KEY`.
- `GET /api/admin/summary` — requires `X-Admin-Token`.

## Production gaps — do not accept live orders yet
Before real customers can pay, add a production database (PostgreSQL), migrations, customer authentication, rate limiting, audit logs, email verification, tax/shipping/returns policies, inventory reservation, payment-gateway checkout and signed webhook verification, order fulfilment, backups, monitoring, privacy/terms pages, and security review. SQLite on ephemeral hosting may lose data. Set exact CORS origins. Never expose API keys or admin tokens in browser code.

The AI assistant currently has no product retrieval or order lookup; it must not be presented as a fully grounded shopping agent. No supplier, stock, shipping, payment, analytics, or sales integrations are configured.
