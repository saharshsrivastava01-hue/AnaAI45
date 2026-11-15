# ULTRA Network — Manual Test Plan

Run the site over HTTPS (GitHub Pages) or localhost in a modern browser.

## Identity registration
1. Register a new label such as `samplecreator`.
2. Confirm the UI reports success and the registry count increments.
3. Attempt to register the same label again; it must be rejected.
4. Try a reserved label such as `admin`; it must be rejected.
5. Try a destination using `http://`; it must be rejected. An HTTPS destination is accepted.

## Cryptographic integrity
1. Resolve the newly created identity; the record signature should verify.
2. Click **Prove key control**; the page should create a fresh nonce and display a proof with `locallyVerified: true`.
3. Export the registry JSON.
4. Change one character in a record's description or destination inside the JSON, then import it. The modified record should be rejected because its signature no longer matches.
5. Import the original export; valid signed public records should be accepted.
6. Remember: the public export does not include private keys. Clearing site data can remove the local private key and prevent future control proofs.

## Alias routing
1. Create an alias pointing to an existing identity.
2. Resolve the alias; it should resolve to the target identity.
3. Attempt to create a duplicate alias; it should be rejected.

## PWA/offline
1. Visit the network page once while online.
2. Install the app if the browser offers an install action.
3. Reload with network disabled; cached shell files should remain available after the service worker has activated.

## Boundaries
- Local uniqueness is not global uniqueness.
- Signature verification checks record integrity against the included public key; it does not establish a real-world person or company identity.
- The prototype does not publish DNS records, provide email hosting, operate authoritative nameservers, or mint a public top-level domain.
- Test on more than one browser before treating the prototype as reliable. No independent security audit has been performed.
