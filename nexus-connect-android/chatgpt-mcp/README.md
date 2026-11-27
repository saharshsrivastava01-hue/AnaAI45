# NEXUS Connect AI — ChatGPT MCP connector

This package exposes a review-first subset of NEXUS backend capabilities as MCP tools. It **does not** call prospects, send email, submit job applications, publish, spend money, or make commitments.

## Run locally
1. Install Node.js 20+.
2. From this folder: `npm install`.
3. Configure environment:
   - `NEXUS_BACKEND_URL` (e.g. `http://127.0.0.1:8080`)
   - `NEXUS_APP_TOKEN` (same bearer token configured in the backend)
   - `PORT` (optional, defaults to 8090)
4. Start: `npm start`.

The server has `GET /health` and an MCP Streamable HTTP endpoint at `/mcp`. For a ChatGPT connector, it must be reachable from the internet over HTTPS, protected by an authentication method supported by the ChatGPT connector configuration. Do not expose this endpoint unauthenticated or publicly with a static secret embedded in a client.

## Tools
- `nexus_health`: backend status
- `nexus_ai_draft`: creates text drafts through backend AI endpoint
- `nexus_list_leads` / `nexus_save_lead`: lead management, no outreach
- `nexus_list_applications` / `nexus_save_application` / `nexus_update_application`: job tracking, no submission
- `nexus_validate_workflow`: plan dependency validation only

## ChatGPT setup (requires user action and eligible account/workspace)
1. Deploy the MCP server and backend on HTTPS, using secret environment variables. Keep backend API token server-side.
2. In ChatGPT, open Settings and the Apps/Connectors area. If developer mode and custom MCP connectors are available for your account/workspace, add the connector URL ending in `/mcp`.
3. Review the authentication options offered by your ChatGPT UI, configure them, and test each tool. Account availability and setup screens may differ.
4. Never allow tools to send messages, apply to jobs, make calls, pay, or publish automatically; review drafts first.

## Limitations
- This is an integration source, not an already-connected ChatGPT app. No cloud deployment or connector authorization has been performed.
- HTTP endpoint currently relies on network deployment protections; configure an authentication gateway / supported MCP auth before exposing publicly.
- Calls endpoint is intentionally not exposed as a tool. The backend voice endpoint is only a static disclosure intro and not a conversational agent.
