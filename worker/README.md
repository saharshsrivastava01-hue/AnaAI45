# ULTRA Worker + D1 API

Cloudflare Worker backend for the static ULTRA frontend. The Worker stores public creator profile metadata, public signed identity records, posts awaiting moderation, and abuse reports. **Private creator signing keys remain in the browser and are never sent to the Worker.**

## Creator ownership and publishing

New creator registration is a proof-of-control flow, not a password or email login:

1. The browser creates an ECDSA P-256 key pair using Web Crypto.
2. The non-exportable private key is stored in that browser's IndexedDB. The public SPKI key and its SHA-256 fingerprint are sent to the Worker.
3. The browser signs a canonical enrollment payload containing the handle, profile fields, timestamp, public key and fingerprint.
4. The Worker verifies the fingerprint and signature before inserting the creator record. The handle and key fingerprint are unique.
5. An operator must approve the profile before it appears in the public directory or can publish.
6. A post includes a fresh timestamp, unique post ID, creator ID and fingerprint. The Worker verifies the signature against the public key bound to that creator ID, then queues the post for moderation. The submitted handle is not trusted as proof of authorship.

The Worker rejects expired signatures, mismatched fingerprints, forged signatures and replayed post IDs. Approved posts only appear in the public feed after operator approval.

### Browser-key limitations

- The private key is marked non-exportable and stays in the browser's IndexedDB; the server stores only the public key.
- This is origin-local storage, not a hardware-backed wallet. JavaScript executing on the same site origin may request signing operations.
- Clearing site data, losing the browser profile or losing the device can permanently lose access. There is currently no encrypted backup, recovery, password login or cross-device transfer.
- Do not register a valuable or business-critical handle until a separately reviewed recovery and key-rotation process exists.
- A valid signature proves control of a cryptographic key; it does not verify a real-world person's identity, company authority or trademark rights.

Existing creator rows created before this change have no owner key. The migration leaves those records intact, but they cannot be newly approved or publish posts until a separate, operator-reviewed ownership-claim process is built. Do not attach a new key to an old handle by trusting a typed handle alone.

## Moderation and abuse reports

- `POST /api/v1/reports` — submit a report.
- `GET /api/v1/moderation/queue` — operator-only pending creator, post and report queue.
- `POST /api/v1/moderation/reports/{id}` — set a pending report to `reviewed` or `dismissed`.
- Each successful report, creator or post status transition is recorded in `moderation_events` in the same D1 batch as the status update. The private queue returns the 50 most recent events.
- Database triggers reject ordinary SQL `UPDATE` and `DELETE` operations against audit rows. This protects against accidental/application-level rewriting; a database administrator can still drop the triggers or alter the database, so this is not tamper-proof or independently immutable storage.
- The current audit actor label is `shared-admin-token`. It records that the shared operator credential was used; it does **not** identify an individual moderator. Individual operator accounts and MFA remain future work.
- `POST /api/v1/moderation/creators/{id}` — approve or reject a pending profile. Approval requires verified owner-key fields.
- `POST /api/v1/moderation/posts/{id}` — approve or reject a pending post.

Every moderation endpoint requires `Authorization: Bearer <ADMIN_TOKEN>`. The Worker fails closed unless `ADMIN_TOKEN` is a 32–128 character URL-safe secret; generate a 64-character hexadecimal value locally with `openssl rand -hex 32`, then enter it with `wrangler secret put ADMIN_TOKEN`. Never put the secret in frontend source, repository files, URL query parameters or local storage. Authentication attempts are limited to 60 per source IP per minute. The operator console sends the token only in an Authorization header and keeps it only in the current page's password field. This remains one shared bearer credential, not individual operator accounts or MFA; use it only on a trusted device.

This is still a prototype moderation system: it does not yet have individual operator identity management, MFA, externally tamper-evident audit storage, appeals, automatic abuse detection or a hardened admin origin. Add those and obtain a security review before public production operation.

## Other API routes

- `GET /health` — health check.
- `GET /api/v1/registry?limit=50&offset=0` — public signed identity registry.
- `GET /api/v1/resolve/{label}` — fetch and verify one identity record.
- `POST /api/v1/identities` — claim a unique label with a signed ECDSA P-256 record.
- `GET /api/v1/creators` — approved creator directory.
- `POST /api/v1/creators` — enroll a key-backed creator profile.
- `GET /api/v1/creators/by-key/{sha256-fingerprint}` — resolve public creator ID, handle and status for a locally stored key; this does not grant write access.
- `GET /api/v1/posts` — approved public posts.
- `POST /api/v1/posts` — submit a post signed by the enrolled creator key.
- `POST /api/v1/ai/chat` — optional server-side model proxy; requires separately configured OpenAI API credentials and can incur provider charges.

The identity registry's self-signed records prove key control, not real-world identity or trademark rights.

## Request and abuse safeguards

- JSON request bodies are read incrementally and capped at 8 KiB for identity, creator, report and moderation endpoints; post submissions and optional AI chat are capped at 20 KiB to accommodate UTF-8 content. AI prompts also have a separate 4,000-character limit.
- Invalid UTF-8, malformed JSON, non-object JSON and oversized bodies are rejected before route-specific database writes.
- Per-IP rate-limit increments and 60-second window resets use one atomic D1 UPSERT with `RETURNING`, avoiding the read-then-write race in the earlier counter implementation.
- CORS returns `Access-Control-Allow-Origin` only for an exact match against `ALLOWED_ORIGIN` or an explicitly configured comma-separated `ALLOWED_DEV_ORIGINS`. Localhost is not implicitly trusted in production; keep development origins out of production configuration.
- Current limits remain prototype defaults: identity claims 10/minute, creator enrollment 5/minute, post submissions 8/minute, abuse reports 5/minute and AI chat 8/minute per IP and operator authentication 60/minute per IP.
- IP rate limiting is still a basic D1 counter, not a distributed abuse-control service. A scheduled Worker handler now deletes at most 500 buckets older than 24 hours per invocation; it is intentionally not activated until an operator adds a Cron Trigger. This bounds each cleanup run and lets later runs continue if more rows remain.

## D1 setup and migration

For a **new database**, create the database, set its ID in `wrangler.toml`, then apply the complete current schema:

```sh
wrangler d1 create ultra-registry
wrangler d1 execute ultra-registry --remote --file=./schema.sql
```

For an **existing database** created from an earlier version of this project, apply the migrations from the `worker` directory in order:

```sh
wrangler d1 execute ultra-registry --remote --file=./migrations/0002_creator_key_ownership.sql
wrangler d1 execute ultra-registry --remote --file=./migrations/0003_moderation_audit_log.sql
wrangler d1 execute ultra-registry --remote --file=./migrations/0004_moderation_audit_immutability.sql
wrangler d1 execute ultra-registry --remote --file=./migrations/0005_rate_limit_retention_index.sql
```

Apply migration 0002 only once; it adds creator public-key/fingerprint fields and post signature audit fields. It does not invent ownership for existing creator rows. Migrations 0003 and 0004 create the moderation event log, indexes and ordinary-DML immutability triggers. Migration 0005 adds the rate-limit retention index. These migrations use `IF NOT EXISTS` and are safe to re-run.

## Worker configuration and deployment

1. Install Node.js 20 or newer and Wrangler.
2. From this directory, run `wrangler login` using the account owner.
3. Create a D1 database if one does not already exist. Set its actual ID in `wrangler.toml`; do not commit credentials.
4. Apply either the new-database schema or the one-time existing-database migration above.
5. Set `ALLOWED_ORIGIN` to the exact HTTPS frontend origin, without a trailing slash.
6. Generate a strong operator token locally with `openssl rand -hex 32`, then set it with `wrangler secret put ADMIN_TOKEN`. The Worker rejects tokens shorter than 32 characters or outside the URL-safe character set.
7. For the optional AI endpoint, set `OPENAI_API_KEY` as a Worker secret and set `OPENAI_MODEL` to a model available to the API account. API billing may be required.
8. To enable rate-limit cleanup, add a Cron Trigger after reviewing the retention policy, for example `[triggers]` with `crons = ["17 * * * *"]` in `wrangler.toml`. Do not enable it until migration 0005 has been applied to the target D1 database.
9. Only after explicit operator approval, deploy with `wrangler deploy` and test `/health`.

No production settings, D1 database or Worker were changed by this code update.

## Tests

From this directory:

```sh
npm test
```

The suite includes Worker route behavior tests with a D1 test double, signature verification, wrong-key rejection, replay rejection, legacy-account approval protection, report moderation authorization, strong operator-token checks, per-IP operator-auth throttling and CORS allowlist behavior. The CI workflow also runs `tests/schema_migrations.test.py` using Python's standard SQLite library to exercise the fresh schema, the ordered existing-database migrations, audit immutability triggers and rollback of an audit/status transaction when its status update fails. SQLite checks improve migration confidence but do not replace a live Cloudflare D1 integration test or external security review.


### Rate-limit bucket retention

The Worker scheduled handler prunes buckets whose `window_started` is more than 24 hours old. It removes no more than 500 rows per invocation; the helper clamps caller-supplied batch sizes to the 1–500 range and bounds retention to 60 seconds–30 days. It uses the index added by migration 0005 (also present in the fresh schema). No Cron Trigger is enabled in the checked-in configuration. After staging verification and explicit approval, an operator may add a Cron Trigger such as `17 * * * *`; each run then removes one bounded batch. The retention period is deliberately longer than the 60-second rate-limit window so expired counters are not removed while they can still affect request decisions.


## Static creator frontend security

The creator page loads its application logic from the same-origin `platform.js` file and declares a Content Security Policy that permits scripts only from the page's own origin. Dynamic creator profiles, posts, reports and moderation queue entries are built with DOM nodes and `textContent`; server-provided strings are not parsed as HTML. The moderation queue status message is kept separate from the action list so refreshing status does not remove the moderation buttons.

The Worker URL field accepts HTTPS URLs only and rejects embedded credentials, query strings and fragments. API requests omit browser credentials, refuse redirects and do not send a referrer. The page still needs a valid HTTPS Worker endpoint and an exact matching Worker CORS origin. This CSP applies to `platform.html`; it does not claim that every other static page in the repository has the same policy. Inline CSS remains allowed on this page for the existing design.

CI checks the CSP declaration, external-script wiring, JavaScript syntax, absence of HTML parsing sinks in `platform.js`, and separation of moderation status from queue content. These static checks do not replace browser testing or a security review.


## Worker API response headers

All Worker API responses, including JSON errors, AI-proxy responses and CORS preflight responses, receive a shared baseline:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- A restrictive API-only Content Security Policy (`default-src 'none'; base-uri 'none'; frame-ancestors 'none'`)
- A Permissions Policy disabling camera, microphone and geolocation
- `Cache-Control: no-store`

These headers protect the JSON API surface; they do not replace the separate Content Security Policy on `platform.html` or secure headers on other static pages. The Worker header tests cover health, not-found, AI configuration-error and untrusted preflight responses. Re-run `npm test` after changing the shared CORS/header builder.
