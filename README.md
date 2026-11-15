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


## Security status update
- Operator moderation now supports marking abuse reports as reviewed or dismissed.
- The duplicate moderation-queue route was removed and bearer-token parsing was corrected.
- Creator post publishing is deliberately disabled until cryptographic creator ownership and post authorisation are implemented. This closes the current handle-impersonation path rather than pretending a handle is an authenticated account.
- Run `node --test worker/tests/security.test.mjs` with Node.js 18+; GitHub Actions runs these static regression checks on pushes and pull requests.
- These source changes are not deployed or integration-tested against a live Cloudflare Worker/D1 database. The static tests check security invariants, not production behavior.


## ULTRA AI assistant (new)
- `ai.html` is the browser chat interface.
- `POST /api/v1/ai/chat` proxies requests through the Cloudflare Worker to the OpenAI API. The provider key stays server-side and is never shipped to the browser.
- Configure the Worker with `wrangler secret put OPENAI_API_KEY` and set `OPENAI_MODEL` to a model available to your API account (for example in `worker/wrangler.toml` under `[vars]`). Do not commit API keys.
- The endpoint limits prompts to 4,000 characters, caps generated output at 900 tokens, and applies a basic per-IP rate limit of 8 requests per minute using D1.
- Open `ai.html`, save the deployed Worker HTTPS base URL, and send a test message.

**Important:** ChatGPT web/app subscriptions do not automatically include API credits. OpenAI API access and billing may need to be configured separately. The assistant is not live until the Worker is deployed and the required secrets/model are configured. API usage may cost money; monitor limits and billing.
