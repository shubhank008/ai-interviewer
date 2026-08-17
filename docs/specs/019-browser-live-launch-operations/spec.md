# Spec 019 - Browser live-launch operations

## What this phase delivers

The platform gains the next operational slice required before a full browser-live launch. Browser authentication, microphone permission, WebSocket connection, and media lifecycle emit stable redacted markers for a real-user rehearsal. Deployment composition gains an explicit frontend service and health checks. Production configuration rejects insecure browser origins and unsafe operational defaults. The release gate reports these checks separately from real-user evidence.

Owner-isolation testing is intentionally excluded from this phase. The browser rehearsal may log authentication and resource identifiers, but it must not claim cross-user isolation until a later authorized test.

## User and operator experience

An operator can build the API and frontend release candidate with one Compose definition, inspect health checks, and run a real browser rehearsal while collecting markers such as `[BROWSER19] auth-restored` and `[BROWSER19] media-ready`. Logs contain event names and redacted identifiers only, never tokens, audio, credentials, or personal data.

## Scope

- Add browser marker logging for Firebase restore/sign-in/sign-out, microphone permission, WebSocket state, and media teardown.
- Add a production frontend container and API/frontend health checks to Compose.
- Enforce production CORS origins as HTTPS origins and reject local/insecure origins.
- Add an operational configuration check for metrics, tracing, retention, rate limiting, and durable storage.
- Add deterministic tests and release-gate markers for the new checks.

## Out of scope

- Cross-user owner-isolation assertions.
- Claiming a deployed provider rehearsal, HTTPS certificate, external monitoring, backup/restore, rollback, or incident response without running it in the target environment.
- Adding credentials, browser automation dependencies, or provider network calls to deterministic tests.

## Acceptance

- [x] Browser marker contract is implemented without sensitive values.
- [x] Compose defines API and frontend health checks and the frontend production service.
- [x] Production configuration fails closed for insecure origins and unsafe operational defaults.
- [x] Deterministic tests and release evidence distinguish implemented checks from unexecuted live evidence.
- [x] Owner isolation remains explicitly deferred, not falsely marked complete.

## Evidence status

The Phase 19 implementation and deterministic gates pass. Docker image builds are not verified in this workspace because the Docker API socket is unavailable. Browser identity, HTTPS, live providers, audio/WebRTC, deployment operations, and target-environment acceptance remain open; this phase does not declare launch readiness.
