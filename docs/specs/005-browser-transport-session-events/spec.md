# Spec 005 - Browser transport and session events

## What the feature is about and what the user experiences

A browser can create or resume an interview session, establish the low-latency audio path, and receive live control and state updates without losing its place when the WebSocket reconnects. The browser uses WebRTC media tracks for microphone input and interviewer audio output. It uses a versioned REST API for setup and retrieval, and a WebSocket for ordered session events, transcript updates, interruptions, playback commands, and safe errors.

A reconnecting browser presents the same authenticated session identity and resumes from its last acknowledged event. The backend replays only events after that cursor, preserves event correlation, and rejects stale or cross-session messages. Signaling messages may travel over the WebSocket, but media bytes never do.

## Numbers

| Value | Number | Source |
|---|---:|---|
| REST API major version | 1 | DESIGN-FRESH |
| Maximum events retained by the deterministic session channel | 256 | DESIGN-FRESH |
| WebSocket replay cursor is inclusive of acknowledged sequence | 1 | DESIGN-FRESH |
| Maximum signaling payload size | 64 KiB | DESIGN-FRESH |

## Out of scope

- A production HTTP framework, browser UI, authentication vendor, database, or Pub/Sub deployment.
- Encoding or tunneling media bytes through WebSocket messages.
- Codec, TURN server, recording, live STT, TTS scheduling, or provider selection decisions.
- External services, credentials, browser automation, or network access in tests.

## Acceptance

- [x] Marker contract written before implementation.
- [x] Versioned REST resources and schemas validate valid and invalid payloads.
- [x] Ordered WebSocket events preserve session and request correlation.
- [x] Reconnect resumes after an acknowledged cursor and rejects wrong-session cursors.
- [x] WebRTC signaling validates offer, answer, and ICE candidates.
- [x] Media transport and control transport are separate provider-independent seams.
- [x] Executable deterministic tests cover schemas, ordering, reconnect, signaling, and separation.
- [x] Required markers print and forbidden failure patterns do not appear.
- [x] Documentation and durable landmines are updated.
