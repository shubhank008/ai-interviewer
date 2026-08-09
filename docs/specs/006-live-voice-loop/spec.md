# Spec 006 - Live voice loop

## What the feature is about and what the user experiences

A candidate can speak naturally while the interviewer listens to incremental speech, responds quickly, and remains grounded in the latest answer. The candidate hears optional short acknowledgements while a substantive response is prepared, followed by ordered speech chunks. If the candidate interrupts, pending generation and playback stop safely and the next response is based on the new answer rather than stale work.

The session preserves final and partial transcript segments, timestamped audio artifacts, and ordered lifecycle events. The browser-facing session event seam can expose response chunks, playback interruption, latency measurements, and provider fallback without carrying media bytes through the control channel.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Maximum secondary response characters | 160 | DESIGN-FRESH |
| Maximum prefetched candidates retained per turn | 2 | DESIGN-FRESH |
| Minimum audio chunk sequence | 0 | DESIGN-FRESH |
| Default synthetic chunk duration | 20 ms | DESIGN-FRESH |
| Timestamp precision | 1 ms | DESIGN-FRESH |

## Out of scope

- Vendor-specific streaming SDKs, credentials, model downloads, network access, or browser automation.
- Production WebRTC media codecs, mixing infrastructure, durable database schemas, and retention enforcement.
- OCR, external research, hidden evaluation scores, or unsupported company claims.
- Guaranteeing real-time wall-clock performance from deterministic CPU-only fixtures.

## Acceptance

- [x] Marker contract is written before implementation.
- [x] Provider-independent streaming interfaces support incremental STT, cancellable LLM generation, secondary responses, and TTS chunks.
- [x] Guarded prefetch results are rejected when their source answer digest is stale.
- [x] Audio scheduling preserves chunk order and stops playback after interruption.
- [x] Final transcript and audio artifacts retain speaker and millisecond timestamps.
- [x] Latency and fallback events are emitted through the existing event seam.
- [x] Unit tests cover every concrete deterministic class and a real mock live-voice turn.
- [x] Evidence prints every required marker and no forbidden failure pattern.
- [x] Documentation, roadmap, and durable landmines are updated.
