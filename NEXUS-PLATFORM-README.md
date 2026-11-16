# NEXUS Global Commerce — API-free prototypes

## NEXUS 5D Commerce OS
Source: https://github.com/saharshsrivastava01-hue/AnaAI45/blob/main/nexus-5d-commerce-os.html

After a successful GitHub Pages deployment, open:
https://saharshsrivastava01-hue.github.io/AnaAI45/nexus-5d-commerce-os.html

Features:
- 5D-inspired responsive visual interface
- Prompt improver machine: rough prompt → structured professional prompt
- Storefront preview, product catalogue manager and demo cart
- Local unpaid demo order ledger
- Campaign copy draft studio and GMV calculator
- JSON backup export and browser-local persistence
- No API key required

## Previous commerce prototype
https://github.com/saharshsrivastava01-hue/AnaAI45/blob/main/nexus-ai-commerce-platform.html

## Honest capability boundaries
These are static, single-browser prototypes. The prompt improver and assistant are deterministic templates, not connected generative AI models and do not call ChatGPT. Data is stored in browser localStorage and is not shared across devices or users. Demo checkout does not charge money, reserve inventory, or create a real order. There is no production backend, cloud database, secure authentication, seller portal, payment gateway, shipping integration, tax engine, supplier feed, or live analytics. No traffic, virality, ranking, sales, or revenue is guaranteed.

## Deploy with GitHub Pages
1. Open repository Settings → Pages: https://github.com/saharshsrivastava01-hue/AnaAI45/settings/pages
2. Set the deployment source to GitHub Actions and save if prompted.
3. Open Actions: https://github.com/saharshsrivastava01-hue/AnaAI45/actions
4. Wait for the Pages deployment workflow to finish with a green successful status.
5. Open the published URL above. A Git commit alone does not publish the website.

## Before real commerce
Add a secure backend/database, authentication and role permissions, verified products/suppliers, inventory controls, privacy notice, customer support, shipping/tax/returns policies and a compliant payment gateway with business/KYC verification. Never store card details in browser storage.

## GMV target math
₹10 crore GMV at ₹2,000 average order value requires 50,000 orders. GMV is gross order value, not profit or revenue retained. Deduct product costs, fulfilment, payment fees, taxes, refunds, marketing and overhead.

## Optional browser-based generative AI
The NEXUS 5D page now includes an opt-in local model loader:
- Model: `onnx-community/LFM2.5-350M-ONNX` (350M parameters)
- Runtime: Transformers.js in the browser; attempts WebGPU, then falls back to CPU/WASM.
- No API key or hosted inference endpoint is required.
- The first use downloads the quantized model files (the model card lists the Q4 weights at approximately 276 MB), plus runtime assets. A stable internet connection is needed for that first download. Browser/device support and available memory affect whether it runs.
- This is inference using a pretrained model, not training or fine-tuning a new NEXUS model. It is a small model and may make mistakes.

Official references:
- Transformers.js browser inference: https://huggingface.co/docs/transformers.js/en/index
- Model card and runtime example: https://huggingface.co/onnx-community/LFM2.5-350M-ONNX

The local model does not add a secure backend, persistent shared customer data, real payment processing, or fulfilment. Do not use it to handle payment credentials or sensitive customer information.
