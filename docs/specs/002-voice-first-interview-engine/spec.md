# Spec 002 - Voice-First Interview Engine

## What the feature is about and what the user experiences

A candidate can start a voice-first mock interview in recruiter or technical mode and receive a coherent opening question. The session knows whether it is ready, active, cancelled, failed, or completed, and it accepts candidate turns only when the session and turn sequence are valid.

As the candidate answers, the engine advances turns in order, emits an ordered lifecycle trail, and prepares the next question from the current mode and latest answer. Prepared follow-ups are guarded: an answer that changes direction invalidates stale preparation instead of allowing an obsolete question to be spoken. A cancellation or provider failure leaves an explicit terminal transition and does not emit a misleading completion event.

This slice is provider-independent. Deterministic Phase 1 providers exercise the real state-machine path without browser transport, vendor services, or persistence.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Supported interview modes | 2 | SPEC.md, section 2.2 |
| First candidate turn sequence | 1 | DESIGN-FRESH |
| Maximum prepared follow-up topics | 1 | DESIGN-FRESH |

## Out of scope

- FastAPI, REST, WebSocket, WebRTC, browser UI, or audio transport integration
- Vendor-specific STT, LLM, TTS, hosting, or provider-routing code
- Persistence, authentication, document parsing, resume/job-description RAG, or evaluation scoring
- Streaming partial transcripts, audio scheduling, interruption at the media layer, or reconnect behavior
- Hiring-manager as a separate enum mode; this slice uses the Phase 1 technical mode

## Acceptance

- [x] Marker contract written (`contracts/log-markers.md`) before implementation
- [x] Session lifecycle supports start, active turn progression, cancellation, failure, and completion
- [x] Recruiter and technical modes produce distinct guarded question plans
- [x] Turn sequencing rejects duplicates, gaps, and turns after terminal state
- [x] Lifecycle events have per-session monotonic ordering and correlation identifiers
- [x] Follow-up preparation is invalidated when the latest answer changes topic
- [x] Behavior-driven unit tests and deterministic mock-turn/state-machine coverage pass
- [x] No vendor, transport, persistence, or secret concerns are introduced
- [x] Available Python test and compilation commands are run; Markdown lint is unavailable in this workspace
