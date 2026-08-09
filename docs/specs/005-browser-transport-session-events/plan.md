# Plan 005 - Browser transport and session events

## Global Constraints

- Follow the SDD lifecycle and keep the marker contract ahead of implementation.
- Keep business logic provider-independent and define interfaces before concrete local implementations.
- Keep WebRTC media separate from WebSocket control and state; never tunnel media bytes through WebSocket.
- Preserve ordered events, correlation IDs, idempotency, reconnect behavior, cancellation, and partial versus final distinctions.
- Keep deterministic tests offline, credential-free, browser-free, and independent of optional Phase 4 packages.
- Maintain focused semantic commits and finish with a clean worktree; `/no-mistakes` owns publication.
- Update `AGENTS.md` with any durable surprise or transport invariant.

## Marker contract

Written in `contracts/log-markers.md` before implementation.

- Requires: `[REST] schemas validated`, `[WS] ordered session events delivered`, `[WS] reconnect replay correlated`, `[WEBRTC] signaling validated`, `[TRANSPORT] media and control separated`.
- Forbids: `Script Error`, `Traceback`, `AssertionError`, `media tunneled over websocket`.

## Work order

1. `docs/specs/005-browser-transport-session-events/` - specify API, event, signaling, and marker contracts.
2. `src/interviewer_domain/transport.py` - add versioned schemas, transport protocols, event channel, reconnect, signaling, and local implementations.
3. `src/interviewer_domain/__init__.py` - expose public transport contracts.
4. `tests/test_browser_transport.py` - exercise all deterministic transport behavior through real local implementations.
5. `PLAN.md`, `README.md`, `AGENTS.md` - record Phase 5 completion, usage, evidence, and landmines.

## Test plan

- Unit: schema validation, resource paths, event ordering and duplicate handling, cursor replay, session correlation, signaling validation, and media/control separation.
- E2E: one deterministic local session creates a REST resource, delivers WebSocket events, reconnects, and negotiates a WebRTC signaling exchange without network access.
- Frames: no visual browser feature is implemented in this phase, so no screenshot evidence is required; marker output is the executable evidence.
