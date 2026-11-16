# NEXUS AI Global Commerce — API-free prototype

## Open
After GitHub Pages is enabled and a deployment succeeds, open:
`https://saharshsrivastava01-hue.github.io/AnaAI45/nexus-ai-commerce-platform.html`

## Included
- Responsive commerce workspace and storefront preview
- Product catalogue stored in browser localStorage
- Test cart and simulated, unpaid order records
- Offline rules-based commerce assistant (no API key)
- Campaign-copy templates
- GMV / order-count calculator
- JSON export
- Web app manifest and service worker for offline caching

## Honest capability boundaries
This is a static, single-browser prototype. The assistant is not a hosted LLM and does not call ChatGPT or any other AI model. Data is not shared across browsers or users. Demo checkout does not take payment, reserve stock, create shipping labels, or place a real order. There is no cloud database, secure authentication, seller portal, live inventory feed, analytics pipeline, tax engine, or production payment integration.

## Deploy free with GitHub Pages
1. Open repository Settings → Pages.
2. Set Build and deployment source to **GitHub Actions** if the repository workflow is configured for Pages.
3. Open Actions, run the Pages deployment workflow, and wait for a green successful run.
4. Use the URL above. A commit alone does not publish the site.

## Before accepting real orders
Add a trusted backend/database, secure authentication and role permissions, verified suppliers and inventory, shipping/tax/returns policies, privacy notice, customer support, and a compliant payment gateway with required business/KYC verification. Never store card details in browser storage. Do not represent demo orders as paid orders.

## Target math
GMV target ₹10,00,00,000 at ₹2,000 average order value requires 50,000 orders. GMV is not revenue retained or profit. Model product cost, fulfilment, payment fees, taxes, refunds, marketing and overhead separately.
