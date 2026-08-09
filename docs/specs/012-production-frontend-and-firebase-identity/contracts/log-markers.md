# Phase 12 marker contract

The deterministic Phase 12 journey must print these exact lines:

- `[PHASE12] auth-local-restored`
- `[PHASE12] setup-validation-ok`
- `[PHASE12] setup-session-created`
- `[PHASE12] interview-controls-ok`
- `[PHASE12] history-resource-ok`
- `[PHASE12] deletion-state-ok`
- `[PHASE12] offline-provider-state-ok`
- `[PHASE12] browser-evidence-ok`

The verification run must not print or contain:

- `Traceback`
- `Script Error`
- `secret leaked`
- `Firebase private key`
- `NotImplementedError`
- `placeholder`
- `skipped required check`

A marker proves a deterministic contract path only. It is not evidence that Firebase, browser media, WebSocket, WebRTC, or external providers are configured.

## Captured evidence

The required markers were emitted by `scripts/test_phase12.sh` on 2026-07-08. Browser frames were captured from the local Vite server after deterministic sign-in. These frames show auth and setup composition only; they do not establish Firebase or browser media readiness.

