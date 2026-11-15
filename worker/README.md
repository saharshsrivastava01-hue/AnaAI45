# ULTRA Shared Registry API

Cloudflare Worker + D1 backend for the ULTRA browser prototype. It stores **public signed identity records only**; private CryptoKeys remain in the user's browser.

## API
- `GET /health` — health check.
- `GET /api/v1/registry?limit=50&offset=0` — public registry page.
- `GET /api/v1/resolve/{label}` — fetch and cryptographically verify one record.
- `POST /api/v1/identities` — claim a globally unique label by submitting a signed public record.

The Worker verifies the ECDSA P-256/SHA-256 signature and public-key fingerprint. D1 enforces unique labels and fingerprints. A self-signed record proves control of a key, not a real-world person's identity or a trademark right.

## Deploy (free-tier account required)
1. Create a Cloudflare account and install Wrangler on a computer with Node.js: `npm install -g wrangler`.
2. From this folder run `wrangler login`.
3. Create the D1 database: `wrangler d1 create ultra-registry`.
4. Copy the returned database ID into `wrangler.toml`, replacing `REPLACE_WITH_YOUR_D1_DATABASE_ID`.
5. Initialize the schema: `wrangler d1 execute ultra-registry --file=./schema.sql`.
6. Set `ALLOWED_ORIGIN` in `wrangler.toml` to the exact HTTPS origin serving the frontend (no trailing slash).
7. Deploy: `wrangler deploy`.
8. Test `https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/health`.

## Connect the frontend
Open `shared.html`, enter the deployed Worker base URL, then import the public JSON exported from `network.html`. Select an identity and publish it to the shared registry. Other visitors can then resolve it from the same Worker URL.

## Security / production notes
- This is an early prototype. Do not use it for valuable identity claims or critical infrastructure.
- Rate limiting here is a basic IP counter in D1, not a robust distributed abuse-control system.
- There is no account login, recovery, ownership transfer, record update/revocation, appeal process, trademark review, or admin moderation UI yet.
- Add monitoring, backups, key rotation/recovery, abuse workflows, security review and terms/privacy pages before public production use.
- Never put private keys or Cloudflare API tokens in frontend code or Git.
