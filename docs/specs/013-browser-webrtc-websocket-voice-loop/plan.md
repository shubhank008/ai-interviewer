# Plan 013 - Usable browser WebSocket and WebRTC voice loop

## Global Constraints

- Preserve abstract-first provider seams and keep vendor imports, credentials, network, and heavyweight media dependencies out of deterministic tests.
- Preserve the Phase 5 invariant that media frames never enter WebSocket payloads; signaling is control only and media uses a separate seam.
- Preserve Phase 6 ordered transcript, cancellation, interruption, fallback, stale-answer, and timestamped-audio behavior.
- Preserve Phase 7 owner checks, retention, persistence, and evaluation boundaries; never expose another user's session.
- Preserve Phase 9 versioned API and Phase 12 local authentication as development fixtures only.
- Keep configured-provider mode explicit and fail safe rather than silently falling back to local mode.
- Keep browser UI, REST, WebSocket, signaling, and media adapters separated and injectable.
- Use focused semantic commits and do not push or create a pull request from this branch.
- Update AGENTS.md only if a durable implementation landmine is discovered.

## Marker contract

Written in `contracts/log-markers.md` before implementation.

- Requires: `[PHASE13] auth-ws-ok`, `[PHASE13] session-envelope-ok`, `[PHASE13] reconnect-replay-ok`, `[PHASE13] heartbeat-cancel-interrupt-ok`, `[PHASE13] transcript-fallback-ok`, `[PHASE13] webrtc-signaling-media-separated-ok`, `[PHASE13] local-browser-e2e-ok`, `[PHASE13] browser-evidence-ok`
- Forbids: `Traceback`, `Script Error`, `secret leaked`, `Firebase private key`, `media tunneled over websocket`, `stale response spoken`, `NotImplementedError`, `placeholder`, `skipped required check`

## Work order

1. `docs/specs/013-browser-webrtc-websocket-voice-loop/` - record user behavior, plan, markers, and evidence requirements.
2. `src/interviewer_domain/transport.py` - extend normalized control commands, ownership, replay, heartbeat, cancellation, interruption, and WebRTC media/signaling seams.
3. `src/interviewer_api/app.py` - add authenticated WebSocket and signaling boundaries backed by owned application state and explicit runtime mode.
4. `frontend/src/api.js`, `frontend/src/transport.js`, and `frontend/src/media.js` - add provider-neutral browser control, reconnect, signaling, microphone, playback, and teardown adapters.
5. `frontend/src/ui.jsx`, `frontend/src/main.jsx`, and `frontend/src/style.css` - connect live controls to transport state, transcript/status events, and safe permission/error states.
6. `tests/test_phase13_browser_voice.py`, existing transport/live tests, and `scripts/test_phase13.sh` - cover real local classes, negative cases, markers, and an in-memory end-to-end path.
7. `README.md`, `SPEC.md`, `PLAN.md`, and operational docs - explain local evidence, configured mode, limitations, and browser evidence.
8. Run lint/typecheck, backend/frontend gates, marker checks, mock-turn checks, browser evidence, and create focused commits.

## Test plan

- Unit: normalized envelopes, ownership, cursors, commands, signaling, media lifecycle, browser client state, and permission/error handling.
- Integration: FastAPI authenticated WebSocket and signaling flow plus real local orchestrator event bridge.
- Negative: unauthorized access, wrong-session replay, reconnect, cancellation, interruption, microphone denial, partial audio, stale response, provider outage, and malformed signaling.
- E2E markers: `scripts/test_phase13.sh` emits every required marker and rejects forbidden patterns.
- Frames: local frontend live room shows connected/reconnecting state, controls, transcript, and status; evidence is saved outside version control.
