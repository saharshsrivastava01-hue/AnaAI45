# Backend setup and API

## Requirements
- Node.js 20+
- An HTTPS deployment target
- OpenAI API key with API billing configured
- Optional Twilio account for outbound PSTN calling

## Local setup
```bash
cd nexus-connect-android/backend
npm install
cp .env.example .env
```
Fill secrets in the local .env file. Never commit .env or copy secrets into Android source.

Generate APP_ACCESS_TOKEN with a secure random generator, for example:
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Start:
```bash
npm start
```

Health check:
```bash
curl http://localhost:8080/health
```

## AI assistant endpoint
Requires Authorization: Bearer APP_ACCESS_TOKEN and OPENAI_API_KEY.

```bash
curl -X POST http://localhost:8080/agent/assist \
  -H "Authorization: Bearer $APP_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task":"draft_proposal","context":"A local cafe wants a simple five-page WordPress website. No budget or deadline has been agreed."}'
```

Allowed task values: qualify_lead, draft_proposal, plan_website, review_scope.
The model returns a JSON-formatted draft. Treat it as untrusted output and review it before sending to a client.

## Outbound call endpoint
This endpoint requires all Twilio credentials, a configured PUBLIC_BASE_URL, a number in OUTBOUND_ALLOWLIST, and explicit userConfirmed=true. It is not a conversational AI call yet.

```bash
curl -X POST https://YOUR_HOST/calls/create \
  -H "Content-Type: application/json" \
  -d '{"to":"+14155550123","userConfirmed":true}'
```

Do not use sample numbers as real prospects. Only call people where contact is lawful and appropriate, identify the AI, respect opt-outs, and comply with local telecom rules.

## Important current limitations
- No database or user-account system yet.
- The app does not yet call /agent/assist; Android-to-backend authentication and API screens remain to be implemented.
- The Twilio voice webhook is a static introductory message, not a two-way AI conversation.
- No Realtime API audio bridge, incoming call handling, FCM notifications, payment gateway, or production deployment is included.
- Do not expose APP_ACCESS_TOKEN, OPENAI_API_KEY, or Twilio credentials in an APK.
