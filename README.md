# ULTRA — Free Creator Discovery Prototype

A zero-cost static prototype for creator discovery, local publishing, ULTRA identity previews and campaign-link drafting.

## Run locally
Open `index.html` in a modern browser. No build tools, API keys, paid services or backend are required.

## Publish free with GitHub Pages
1. Open the repository Settings → Pages.
2. Under Build and deployment, choose Deploy from a branch.
3. Select branch `main` and folder `/ (root)`, then Save.
4. Wait for GitHub Pages to publish. The expected project URL is `https://saharshsrivastava01-hue.github.io/AnaAI45/`.
5. Test the URL on mobile and desktop.

## Important limitations
- Posts and claimed identities are saved only in the current browser's localStorage. They are not shared across users or devices.
- This is a static prototype: no account system, database, server-side registry, video hosting, server analytics or moderation backend.
- `name.ultra` is an internal ULTRA namespace label, not a public DNS top-level domain. Its share link is a normal HTTPS URL on the GitHub Pages host.
- No Google indexing, ranking, virality, AdSense approval or revenue is guaranteed.
- A GitHub Pages subdomain is not automatically eligible for ordinary AdSense site registration. Google makes the final eligibility and approval decision. Use a domain/host supported by Google's current signup flow and verify ownership.

## Before a real launch
Add a secure backend and authentication, shared database with row-level access controls, server-side public profile/content routes, upload storage, moderation/reporting, privacy/terms/contact details, real analytics, canonical host configuration, sitemap generation and security review. Publish original useful content before requesting indexing or applying for advertising.

## Search engine files
The repository includes `robots.txt` and `sitemap.xml`. Update the sitemap last-modified date and URLs whenever the public site structure changes.
