# NEXUS Connect AI — Android starter

A Kotlin Android starter for a consent-based client calling assistant.

## What this starter does
- Runs as a native Android app (Android Studio / Gradle).
- Lets the user enter a client phone number and open the system dialer with the number prefilled. The user must tap Call.
- Opens Google Meet's new-meeting page (`https://meet.google.com/new`) so the user can create or join a video meeting and choose participants.
- Includes an optional backend call-request screen contract for a future Twilio + OpenAI Realtime integration.
- Does **not** create a meeting automatically, secretly place calls, bypass carrier permissions, impersonate the user, connect AI audio to a live call, or guarantee paid work.

## Real AI phone calls: production requirements
1. A telephony provider account and a phone number (for example Twilio); calls are paid and availability/regulatory requirements vary by country.
2. A deployed HTTPS backend holding provider credentials as environment secrets.
3. A WebSocket media bridge between the provider's call media stream and the OpenAI Realtime API.
4. Clear AI disclosure, lawful calling consent, opt-out handling, caller-ID compliance, recording notice where required, rate limits, and human handoff.
5. A user-controlled approval step before outbound calls, quotes, contracts, or commitments.

The backend folder contains a safe setup scaffold. It deliberately refuses to place calls until credentials and an explicit allowlist are configured.

## Build
Open this folder in Android Studio. Use JDK 17 and Android Gradle Plugin 8.6.1 / Gradle 8.7. Sync, then run on your Android phone with USB debugging enabled.

## Current communication controls
The Android screen provides two explicit user actions: open the system dialer with a supplied number, and open Google Meet's new-meeting page. The app does not know whether a call or meeting was actually started, and it does not invite contacts automatically.

## Next milestone
Add authenticated user accounts, secure token storage, push notifications for incoming calls, call history, and the Realtime media bridge. Do not put API keys or Twilio auth tokens in the Android app.