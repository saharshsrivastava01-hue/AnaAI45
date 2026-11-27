# NEXUS Connect AI — architecture

## Product goal
A consent-based Android client workspace that helps a freelancer speak with prospects, qualify website requirements, prepare proposals, and track delivery. It is an assistant, not an autonomous employee or guaranteed income source.

## System components
- Android app: Kotlin UI, dialer handoff, secure API calls, client records, approval screens.
- Backend: Node.js/Express, authentication, AI orchestration, call-provider adapter, audit trail.
- Telephony: Twilio Programmable Voice or another provider available to the account and country.
- Conversational AI: OpenAI Realtime API connected through a server-side media bridge.
- Storage: PostgreSQL for users, leads, consent records, call metadata, proposals, tasks, and audit events.
- Notifications: Firebase Cloud Messaging for incoming call/task status notifications.
- Website delivery: isolated project workspace, Git integration, preview deployment, tests, and explicit customer approval.

## Call lifecycle
1. User selects a lead and reviews the number, country, purpose, and script.
2. App checks consent / lawful basis, suppression list, time window, and configured allowlist.
3. User explicitly approves the outbound call.
4. Backend creates the provider call and records provider call ID.
5. Provider streams audio to the backend over an authenticated WebSocket.
6. Backend bridges audio/events to OpenAI Realtime; secrets remain server-side.
7. AI identifies itself as AI, asks whether it is a convenient time, and honors stop/do-not-call requests.
8. AI may collect requirements and draft a follow-up. A human approves any price, scope, deadline, contract, or commitment.
9. Call summary and next actions are stored with retention controls.

## Security requirements before production
- HTTPS and WSS only; never expose OpenAI or telephony secrets in Android.
- Per-user authentication, short-lived access tokens, refresh-token rotation, rate limiting.
- Verify provider webhook signatures; reject forged requests.
- Encrypt sensitive records at rest; minimize stored personal data.
- Explicit recording disclosure and local-law review before recording.
- Consent and do-not-call suppression; no bulk unsolicited robocalling.
- Audit every outbound call and every AI-proposed action.
- Human confirmation before calls, emails, quotes, purchases, contracts, or deployments.
- Secret rotation, backups, monitoring, abuse reporting, and incident response.

## Delivery milestones
- M0: Android dialer handoff and backend call scaffold (source committed).
- M1: authenticated AI work-assistant API and proposal/task workflows.
- M2: persistent database, user authentication, lead/task UI, audit events.
- M3: provider webhook signature validation and compliant call lifecycle.
- M4: real-time media bridge and Realtime API session orchestration.
- M5: push notifications, incoming call handling, testing, deployment, and security review.
- M6: website project sandbox, preview builds, QA, client acceptance, and payment links.

## Not implemented yet
This repository does not yet contain a deployed backend, provider account, real-time audio bridge, incoming-call push handling, persistent database, payment processing, or production-ready app binary. Source code alone does not activate these services.
