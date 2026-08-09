# Spec 013 - Usable browser WebSocket and WebRTC voice loop

## What the feature is about and what the user experiences

After authenticated setup, a candidate enters a live room with an explicit connection state. The browser opens an owned session control channel, resumes from its last acknowledged event after reconnect, and shows heartbeat, transcript, provider, interruption, and error status without exposing audio bytes in control messages. A separate WebRTC media boundary carries microphone tracks and interviewer playback; permission denial, partial audio, provider outage, cancellation, and teardown are visible and safe.

The local browser mode exercises the same REST, WebSocket, WebRTC-signaling, and UI contracts with deterministic in-memory seams. Configured-provider mode is explicit: unavailable credentials, transports, or media capabilities produce an actionable unavailable state and never silently become local mode.

## Numbers

| Value | Number | Source |
|---|---:|---|
| API/WebSocket major version | 1 | Existing Phase 5 and Phase 9 contracts |
| Event replay retention | 256 events | Existing Phase 5 design constant |
| Signaling payload maximum | 64 KiB | Existing Phase 5 design constant |
| Heartbeat interval | 15 seconds | DESIGN-FRESH |
| Maximum reconnect attempts | 3 | DESIGN-FRESH |

## Out of scope

- Claiming Firebase, TURN, real microphone, WebRTC network, or hosted-provider readiness without configured integration evidence.
- Sending media frames or encoded audio bytes through WebSocket control payloads.
- Vendor SDKs, browser automation dependencies, network calls, credentials, or heavyweight media models in deterministic tests.
- Production TURN infrastructure, codec selection, recording storage implementation beyond existing provider seams.

## Acceptance

- [ ] Marker contract written before implementation
- [ ] Authenticated WebSocket ownership, normalized envelopes, sequence cursors, replay, heartbeat, cancellation, interruption, and stale-response rejection work through injected seams
- [ ] WebRTC offer/answer/ICE signaling and separate media-track lifecycle are provider-neutral and teardown-safe
- [ ] Partial/final transcripts and provider fallback statuses reach the browser control channel
- [ ] Local browser mode exercises REST/WebSocket/WebRTC/UI contracts without credentials or media bytes in deterministic tests
- [ ] Negative tests cover unauthorized access, reconnect, cancellation, microphone denial, partial audio, stale responses, and provider outage
- [ ] Browser evidence shows live controls, connection state, and transcript/status updates
- [ ] Required gates and Phase 13 marker checks pass; configured-versus-local limitations remain explicit
