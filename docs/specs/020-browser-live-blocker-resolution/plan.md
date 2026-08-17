# Plan 020 - Browser live blocker resolution

## Global constraints

- Do not claim launch readiness without target-environment browser and operations evidence.
- Keep owner isolation deferred and never represent markers as proof of isolation.
- Keep secrets, tokens, audio, transcripts, and personal data out of logs and evidence.
- Keep deterministic tests offline and use injected browser/provider seams.
- Use the existing REST, WebSocket, media, persistence, and provider interfaces.

## Work order

1. Define this spec, plan, and marker contract.
2. Connect microphone capture and authenticated media chunks to the live room.
3. Execute turn-start and completion calls through the existing session boundaries.
4. Add durable expired-record enumeration and owner-scoped retention cleanup.
5. Implement or validate WebRTC/TURN negotiation, secure-origin enforcement, deployed CORS, secrets, rate limits, and observability.
6. Add targetable browser rehearsal evidence and update the release gate.
7. Run full deterministic validation, attempt Docker/provider validation, and report environment blockers.

## Test plan

- Unit: frontend media capture, teardown, URL construction, persistence expiration, and storage cleanup.
- Integration: authenticated ASGI media, control, completion, and resource paths.
- Live: browser HTTPS login, microphone, WebSocket reconnect, TURN/WebRTC, configured providers, CORS, rate limits, and operational checks.
- Evidence: redacted markers only; browser screenshots/frames are required for visual launch review.
