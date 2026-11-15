# ULTRA Identity Protocol — Prototype v1

## Purpose
ULTRA is a platform-managed namespace for memorable labels such as `alice.ultra`. In this prototype, a label resolves through a normal HTTPS URL hosted by the project. It is not a public DNS top-level domain, a registrar, an ICANN registry, or a replacement for DNS.

## Signed identity record
Each local identity record contains:
- namespace and normalized label
- optional HTTPS destination and description
- created timestamp and record version
- ECDSA P-256 public key (SPKI)
- SHA-256 public-key fingerprint
- ECDSA/SHA-256 signature over deterministic JSON fields

The private CryptoKey is non-exportable and stored in browser IndexedDB. The browser never uploads it. Clearing browser data can make the private key unavailable. This is a prototype key-management design, not a hardware-backed wallet or audited security product.

## Trust boundaries
- Local registry: browser-local only; availability is not globally authoritative.
- Resolver: verifies that a record's signature matches its embedded public key and fingerprint. A self-signed record proves integrity relative to that key, not the real-world identity of its creator.
- Aliases: local convenience mappings; they are not independently signed or globally replicated.
- Hosting: HTTPS transport and GitHub Pages availability do not create DNS delegation.

## Production architecture required
1. Authenticated account and ownership recovery.
2. PostgreSQL registry with unique normalized-label constraint and transactional registration.
3. Signed registry events, append-only audit history, key rotation/revocation and recovery.
4. RLS/authorization, rate limits, anti-squatting policy, reserved-name policy, abuse reports and appeals.
5. Public resolver API, cache and replicated read-only resolver nodes.
6. Optional DNS integration only under a real domain controlled by the operator; never claim .ultra works in the public DNS root without formal delegation.
7. Monitoring, backups, incident response and independent security review.

## Local development
Open `network.html` over HTTPS (or localhost) in a modern browser. The Web Crypto API and IndexedDB are required for signing. The service worker enables basic offline caching after the first successful load.


## Proof of key control
The resolver can generate a random 192-bit nonce, bind it to the namespace, label, public-key fingerprint and issue time, then sign the challenge with the locally stored private key. The page verifies that signature locally and displays a JSON proof object. This demonstrates local possession of the key at proof-generation time. It is not a server-issued timestamp, trusted identity check, remote authentication service or anti-replay system until a server stores and consumes challenges.
