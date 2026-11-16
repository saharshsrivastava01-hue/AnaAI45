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
- `POST /api/v1/moderation/creators/{id}` — approve or reject a pending profile. Approval requires verified owner-key fields.
- `POST /api/v1/moderation/posts/{id}` — approve or reject a pending post.

Every moderation endpoint requires `Authorization: Bearer <ADMIN_TOKEN>`. Configure the secret with `wrangler secret put ADMIN_TOKEN`; never put it in frontend source, repository files, URL query parameters or local storage. The operator console sends it in an Authorization header and keeps it only in the current page's password field. Use it only on a trusted device.

This is still a prototype moderation system: it does not yet have operator identity management, MFA, durable moderation audit logs, appeals, automatic abuse detection or a hardened admin origin. Add those and obtain a security review before public production operation.

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

The identity registry's self-signed records prove key control, not real-world identity or trademark rights. The IP rate limiter is a basic D1 counter, not a distributed abuse-control service.

## D1 setup and migration

For a **new database**, create the database, set its ID in `wrangler.toml`, then apply the complete current schema:

```sh
wrangler d1 create ultra-registry
wrangler d1 execute ultra-registry --remote --file=./schema.sql
```

For an **existing database** created from an earlier version of this project, apply the one-time migration from the `worker` directory:

```sh
wrangler d1 execute ultra-registry --remote --file=./migrations/0002_creator_key_ownership.sql
```

Do not apply that migration more than once. It adds creator public-key/fingerprint fields and post signature audit fields. It does not invent ownership for existing creator rows.

## Worker configuration and deployment

1. Install Node.js 20 or newer and Wrangler.
2. From this directory, run `wrangler login` using the account owner.
3. Create a D1 database if one does not already exist. Set its actual ID in `wrangler.toml`; do not commit credentials.
4. Apply either the new-database schema or the one-time existing-database migration above.
5. Set `ALLOWED_ORIGIN` to the exact HTTPS frontend origin, without a trailing slash.
6. Set the operator secret: `wrangler secret put ADMIN_TOKEN`.
7. For the optional AI endpoint, set `OPENAI_API_KEY` as a Worker secret and set `OPENAI_MODEL` to a model available to the API account. API billing may be required.
8. Only after explicit operator approval, deploy with `wrangler deploy` and test `/health`.

No production settings, D1 database or Worker were changed by this code update.

## Tests

From this directory:

```sh
npm test
```

The suite includes Worker route behavior tests with a D1 test double, signature verification, wrong-key rejection, replay rejection, legacy-account approval protection and report moderation authorization. It does not replace a live Cloudflare D1 integration test or external security review.
