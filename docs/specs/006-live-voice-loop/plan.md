# Plan 006 - Live voice loop

## Global Constraints

- Follow the SDD lifecycle: spec, plan, marker contract, implementation, evidence, documentation, and landmine review.
- Define abstract capability seams before concrete deterministic providers; no vendor names or optional imports in business logic.
- Reuse Phase 1 normalized errors, cancellation, transcript, recording, lifecycle, and provider contracts.
- Reuse Phase 2 session planning and state-machine guards; stale substantive questions must never be spoken.
- Reuse Phase 4 fallback semantics and keep optional provider packages, credentials, downloads, and network calls out of imports and tests.
- Reuse Phase 5 control and media separation; media bytes stay outside WebSocket event payloads.
- Keep tests CPU-only, deterministic, credential-free, network-free, browser-free, and independent of heavyweight models.
- Preserve ordering, correlation, idempotency, cancellation, partial/final distinctions, and sensitive-data boundaries.
- Keep focused semantic commits, update `PLAN.md`, and let `/no-mistakes` own publication.
- Record any new durable surprise in `AGENTS.md` before completion.

## Marker contract

Written in `contracts/log-markers.md` before implementation.

- Requires: `[LIVE] incremental STT connected`, `[LIVE] cancellable response streamed`, `[LIVE] stale prefetch rejected`, `[LIVE] audio chunks ordered`, `[LIVE] interruption stopped playback`, `[LIVE] artifacts timestamped`, `[LIVE] latency measured`, `[LIVE] provider fallback emitted`, `[LIVE] mock turn complete`.
- Forbids: `Script Error`, `Traceback`, `AssertionError`, `stale response spoken`, `media tunneled over websocket`.

## Work order

1. `docs/specs/006-live-voice-loop/` - specify user behavior, constraints, work order, and executable markers.
2. `src/interviewer_domain/contracts.py` - add streaming capability protocols and normalized chunk values.
3. `src/interviewer_domain/live_voice.py` - implement orchestration, prefetch guards, scheduling, artifacts, latency, and fallback events.
4. `src/interviewer_domain/providers.py` - add deterministic streaming fixtures for STT, LLM, secondary response, and TTS.
5. `src/interviewer_domain/__init__.py` - export public Phase 6 contracts and orchestration.
6. `tests/test_live_voice.py` - cover concrete fixtures and a real end-to-end mock live turn.
7. `PLAN.md`, `README.md`, `AGENTS.md` - document completion, evidence, and landmines.

## Test plan

- Unit: incremental transcript ordering, cancellation, secondary response bounds, digest-guarded prefetch, TTS chunk ordering, interruption, artifact timestamps, latency, and fallback.
- E2E: run the real orchestrator with deterministic streaming providers and an in-memory event bus/storage seam; assert state, artifacts, event payloads, and all markers.
- Frames: no visual UI is implemented; marker output is the executable evidence.
