# Plan 012 - Production frontend and Firebase identity

## Global Constraints

- Follow the SDD lifecycle and keep focused semantic commits; do not push or create a PR from this branch.
- Keep provider interfaces before integrations. Firebase auth must be behind an injectable `AuthProvider` seam and remain credential-free in default tests.
- Preserve the Phase 5 media/control boundary: this UI must not put media bytes in API or WebSocket event payloads.
- Preserve Phase 6 transcript ordering, cancellation, interruption, and reconnect semantics as UI states rather than inventing a second interview engine.
- Preserve Phase 7 owner checks, 5 MB PDF validation, 14-day retention, and complete deletion semantics.
- Preserve Phase 9 versioned API calls and local development bearer authentication as a development fixture only.
- Preserve Phase 11 explicit local versus production configuration and never imply provider readiness from offline evidence.
- Keep visual components separate from API clients, auth state, transport adapters, and domain behavior.
- Avoid network, credentials, browser automation, and heavyweight dependencies in deterministic tests.
- Update AGENTS.md only when implementation reveals a durable surprise.

## Marker contract

Written in `contracts/log-markers.md` before implementation.

- Requires: `[PHASE12] auth-local-restored`, `[PHASE12] setup-validation-ok`, `[PHASE12] setup-session-created`, `[PHASE12] interview-controls-ok`, `[PHASE12] history-resource-ok`, `[PHASE12] deletion-state-ok`, `[PHASE12] offline-provider-state-ok`, `[PHASE12] browser-evidence-ok`
- Forbids: `Traceback`, `Script Error`, `secret leaked`, `Firebase private key`, `NotImplementedError`, `placeholder`, `skipped required check`

## Work order

1. `docs/specs/012-production-frontend-and-firebase-identity/` - record user behavior, constraints, markers, and evidence requirements.
2. `frontend/src/api.js` - expand versioned resource request builders and upload/delete seams without visual concerns.
3. `frontend/src/auth.js` - add provider-neutral auth contract, deterministic local profile, and optional Firebase-shaped adapter boundary.
4. `frontend/src/ui.jsx` and `frontend/src/style.css` - build the token/component layer, protected application shell, setup, live, history, results, account, and state surfaces.
5. `frontend/src/main.jsx` - compose auth, API, transport, and visual state while preserving a small root entrypoint.
6. `frontend/src/*.test.js` and `scripts/test_phase12.sh` - cover public behavior, markers, and deterministic local journey without source-string assertions.
7. `README.md`, `SPEC.md`, `PLAN.md`, and operational docs - explain local versus configured identity, routes, evidence, and limitations.
8. Run focused checks, all required gates, browser evidence, inspect forbidden patterns, and create focused semantic commits.

## Test plan

- Unit: request builders, auth provider behavior, setup validation, resume validation, and state transitions through real functions.
- Integration: run a local FastAPI server and Vite frontend, exercise protected setup and history behavior with deterministic local auth.
- E2E markers: run the Phase 12 script and assert exact marker output and forbidden-pattern absence.
- Frames: capture the primary setup journey and authenticated application shell with browser tooling; save evidence outside version control.

## Evidence captured

- `./scripts/test_phase12.sh` emitted all eight required markers with no forbidden patterns.
- `npm run test:coverage --prefix frontend` passed 8 tests at 85.89% lines, 96% branches, 80% functions, and 85.89% statements.
- `npm run lint --prefix frontend` and `npm run build --prefix frontend` passed.
- Browser frames: `/home/openhands/.openhands/agent-canvas/conversations/067dc08685fd4d25a5d690c3f62dd0d9/observations/browser_screenshot_be852a3d.png` (auth) and `browser_screenshot_39089e7e.png` (authenticated setup).
- No Firebase SDK credentials, browser media transport, or external provider evidence was introduced.

