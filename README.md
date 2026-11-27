# ULTRA — Free Creator Platform & Identity Network

A zero-cost static prototype for creator discovery, local publishing, campaign-link drafting, and a NEXORA-inspired identity namespace.

## Open the app
- Home: `index.html`
- Identity registry and resolver: `network.html`
- Protocol design: `ULTRA-PROTOCOL.md`

## New identity-network capabilities
- Local identity labels such as `alice.ultra` with reserved-name protection.
- HTTPS destination mapping and local alias routing.
- ECDSA P-256 / SHA-256 signed identity records using the browser Web Crypto API.
- SHA-256 public-key fingerprints and signature verification.
- Non-exportable private keys stored locally in IndexedDB.
- Portable JSON export/import for signed public records; invalid signatures are rejected on import.
- PWA manifest and service worker for installability and basic offline caching.

## Run locally
Open `index.html` or `network.html` in a modern browser. For cryptography and service-worker features, use HTTPS or localhost. No paid API or build tools are required.

## Publish free with GitHub Pages
1. Open repository Settings → Pages.
2. Under Build and deployment, select **GitHub Actions** if the workflow is enabled, or deploy from branch `main` and folder `/ (root)`.
3. Wait for the Pages workflow to complete.
4. Test `https://saharshsrivastava01-hue.github.io/AnaAI45/` and the `network.html` page.

## Critical limitations
- The registry and posts are browser-local. They are not shared across users/devices; local name availability is not globally authoritative.
- A self-signed record proves integrity relative to its embedded public key. It does not prove a person's real-world identity or ownership of a brand.
- Private keys are non-exportable and stored in browser IndexedDB. Clearing browser/site data may make an identity key unrecoverable. Exporting the public registry does not back up private keys.
- This is not a public DNS registrar or registry. `alice.ultra` is an internal ULTRA namespace label that resolves through an ordinary HTTPS URL. It is not an ICANN-delegated TLD and will not resolve in arbitrary browsers or DNS clients.
- A public gTLD requires formal ICANN processes, a qualified registry operator and substantial operational/financial resources. The 2026 ICANN new-gTLD round has closed; see the official program and fee information.
- No Google indexing, ranking, virality, AdSense approval or revenue is guaranteed. A GitHub Pages subdomain is not automatically eligible for ordinary AdSense signup.

## Production roadmap
To become a genuine multi-user service, ULTRA still needs authenticated accounts, a shared database with atomic unique-label constraints, ownership recovery, key rotation/revocation, signed audit history, resolver API, abuse prevention, moderation, backups, monitoring, independent security review and an operator-controlled domain. Optional DNS records can only be published under a real domain for which the operator controls authoritative DNS.

## Search engine files
The repository includes `robots.txt` and `sitemap.xml`. Only meaningful public pages should be indexed; do not generate thin pages for every unused name.


## Shared registry backend (new)
- `shared.html` — browser dashboard for publishing signed identities to, and resolving identities from, the shared API.
- `worker/src/index.js` — Cloudflare Worker REST API with signature verification, IP-based basic rate limiting and unique-name claims.
- `worker/schema.sql` — Cloudflare D1 schema with unique identity labels and key fingerprints.
- `worker/wrangler.toml` and `worker/README.md` — deployment configuration and step-by-step setup.

The shared API is **source code only until deployed**. To activate it, create a Cloudflare D1 database, set its ID in `worker/wrangler.toml`, run the SQL schema, deploy the Worker, and enter its URL in `shared.html`. Never put Cloudflare secrets in browser code or Git. The free-tier availability and limits are controlled by Cloudflare and may change.


## Creator Network and publishing (new)
- `platform.html` — creator directory, public feed, profile submission, post submission and abuse reporting UI.
- Worker endpoints: `GET /api/v1/creators`, `POST /api/v1/creators`, `GET /api/v1/posts`, `POST /api/v1/posts`, `POST /api/v1/reports`.
- Creator profiles and posts enter a pending queue; only approved content appears in public directory/feed.
- Moderation endpoints require the Worker secret `ADMIN_TOKEN`. Configure it with `wrangler secret put ADMIN_TOKEN`.
- Apply the updated `worker/schema.sql` to an existing D1 database to create the community tables.

This is not yet a complete login/account system. Profile/post submissions are rate-limited and moderated, but a production launch still needs authenticated creator ownership, stronger anti-abuse controls, privacy/terms pages, backup and security review.


The creator platform now includes a token-protected moderation queue at `GET /api/v1/moderation/queue`; the operator UI in `platform.html` can approve or reject pending creator profiles and posts. Reports are listed for review but are not automatically resolved.


## Security status update (27 Nov 2026)
- Abuse reports can be marked `reviewed` or `dismissed` only by the operator; successful moderation transitions are recorded with the status change in a D1 batch and exposed in the private moderation queue.
- New creator handles are bound to ECDSA P-256 public keys after a fresh signed enrollment proof. Posts must be signed by the key bound to the approved creator ID; handle-only publishing is not accepted.
- Legacy creator rows remain unowned. They cannot be approved for publishing until a separate reviewed ownership-claim process exists; no typed-handle claim is trusted.
- The operator console uses one shared bearer secret with request throttling and an explicit page-session Worker-endpoint trust confirmation. This is not individual moderator authentication or MFA.
- For a new D1 database, apply `worker/schema.sql`. For an existing database, apply migrations `0002`–`0006` in order; migration `0002` is one-time only and must not be blindly rerun.
- Run `cd worker && npm test` and `python3 tests/schema_migrations.test.py`. CI uses a D1 test double plus SQLite migration checks; these are not live Cloudflare D1 or browser end-to-end tests.
- These are committed source changes only. No Worker deployment, D1 migration, Pages configuration or production setting is changed by this PR.


## ULTRA AI assistant (new)
- `ai.html` is the browser chat interface.
- `POST /api/v1/ai/chat` proxies requests through the Cloudflare Worker to the OpenAI API. The provider key stays server-side and is never shipped to the browser.
- Configure the Worker with `wrangler secret put OPENAI_API_KEY` and set `OPENAI_MODEL` to a model available to your API account (for example in `worker/wrangler.toml` under `[vars]`). Do not commit API keys.
- The endpoint limits prompts to 4,000 characters, caps generated output at 900 tokens, and applies a basic per-IP rate limit of 8 requests per minute using D1.
- Open `ai.html`, save the deployed Worker HTTPS base URL, and send a test message.

**Important:** ChatGPT web/app subscriptions do not automatically include API credits. OpenAI API access and billing may need to be configured separately. The assistant is not live until the Worker is deployed and the required secrets/model are configured. API usage may cost money; monitor limits and billing.
