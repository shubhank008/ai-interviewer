# Spec 020 - Browser live blocker resolution

## What this phase delivers

The browser interview path executes the user journey rather than only emitting lifecycle markers. A candidate can grant microphone access, stream recorded microphone chunks through the authenticated media channel, start an interview turn, stop capture, complete the interview through the API, and reach results only after completion succeeds. Expired interviews are removed by an owner-scoped retention coordinator from durable metadata and storage.

This phase also defines the remaining release proof: real browser HTTPS, TURN/WebRTC connectivity, configured providers, Firebase login, deployed CORS, rate-limit behavior, and operational observability must be exercised in the target environment before launch is declared.

## User and operator experience

A candidate sees a connected live room with an explicit microphone permission action, an enabled answer control only after the control channel and microphone are ready, and a stop action that completes the session before navigating to results. Operators can run retention cleanup against local or Firestore-backed records without deleting another owner's data or leaving owner-scoped artifacts behind.

## Scope

- Connect browser microphone capture to the authenticated binary media WebSocket.
- Start real turn commands only when the control connection and microphone capture are ready.
- Complete sessions through the authenticated completion API and keep the room open when completion fails.
- Add durable expired-record enumeration and owner-scoped storage cleanup.
- Define executable evidence markers for browser, HTTPS, TURN/WebRTC, providers, CORS, rate limits, and retention operations.
- Preserve owner-isolation browser testing as deferred, as previously authorized.

## Out of scope

- Claiming browser, HTTPS, TURN, provider, Firebase, deployed CORS, or observability readiness without target-environment evidence.
- Replacing the provider-neutral media boundary with vendor-specific browser code.
- Adding credentials, audio bytes, or personal data to logs or deterministic fixtures.
- Owner-isolation testing in the browser.

## Acceptance

- [x] Browser microphone chunks use an authenticated media endpoint and are torn down safely.
- [x] Live-room turn and completion controls call the real session transport and API boundaries.
- [x] Local and Firestore persistence expose expired records for retention administration.
- [x] Persistence cleanup deletes owner-scoped storage prefixes and metadata.
- [ ] Browser HTTPS and Firebase login pass in the target deployment.
- [ ] TURN/WebRTC offer, answer, ICE, and media connectivity pass in the target deployment.
- [ ] Configured STT, TTS, and LLM providers pass the browser journey.
- [ ] Deployed CORS, rate limits, secrets, and observability pass operational checks.

## Evidence status

Local deterministic evidence is passing for the implemented slices. Docker access is permission-blocked in this workspace, and no target browser, HTTPS certificate, TURN service, Firebase login, configured-provider browser journey, deployed CORS, or live operations evidence has passed. This phase does not declare launch readiness.
