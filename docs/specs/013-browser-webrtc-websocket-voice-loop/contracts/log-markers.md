# Phase 13 marker contract

The deterministic Phase 13 journey must print these exact lines:

- `[PHASE13] auth-ws-ok`
- `[PHASE13] session-envelope-ok`
- `[PHASE13] reconnect-replay-ok`
- `[PHASE13] heartbeat-cancel-interrupt-ok`
- `[PHASE13] transcript-fallback-ok`
- `[PHASE13] webrtc-signaling-media-separated-ok`
- `[PHASE13] local-browser-e2e-ok`
- `[PHASE13] browser-evidence-ok`

The verification run must not print or contain:

- `Traceback`
- `Script Error`
- `secret leaked`
- `Firebase private key`
- `media tunneled over websocket`
- `stale response spoken`
- `NotImplementedError`
- `placeholder`
- `skipped required check`

Markers prove deterministic local behavior only. They do not prove real microphone access, WebRTC connectivity, Firebase identity, TURN deployment, or configured production-provider readiness.
