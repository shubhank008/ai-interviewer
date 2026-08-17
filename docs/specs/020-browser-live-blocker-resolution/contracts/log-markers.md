# Phase 20 marker contract

## Required markers

- `[BROWSER20] microphone-capture-started`
- `[BROWSER20] microphone-capture-stopped`
- `[BROWSER20] turn-started`
- `[BROWSER20] interview-completed`
- `[RETENTION20] expired-records-purged`
- `[LIVE20] https-origin-verified`
- `[LIVE20] firebase-login-verified`
- `[LIVE20] websocket-reconnect-verified`
- `[LIVE20] turn-webrtc-verified`
- `[LIVE20] providers-verified`
- `[LIVE20] cors-verified`
- `[LIVE20] rate-limit-verified`
- `[LIVE20] observability-verified`

## Redaction rules

Markers may include event names, counts, durations, provider names, and opaque test-run IDs only. They must not include tokens, credentials, audio bytes, transcript text, email addresses, user IDs, document names, or raw provider payloads.

## Forbidden evidence

- A deterministic marker may not be described as target-environment proof.
- Missing Docker, browser, Firebase, TURN, provider, HTTPS, or deployment evidence must remain an explicit blocker.
- Owner-isolation claims are forbidden in this phase.
