# Spec 009 - Production hardening

## What the feature is about and what the user experiences

A developer can start the interview platform locally with documented commands, open a browser interface, create an interview, exercise the mock voice loop, inspect history, transcript, replay, and evaluation results, and receive safe health and version responses from the API. Operators have deterministic evidence for the complete pipeline, provider failures, reconnects, cancellation, partial audio, authorization, retention, rate limits, latency, cost, and resource usage without credentials, network access, browser automation, or heavyweight models.

The production boundary is explicit: FastAPI exposes versioned health, version, session, history, transcript, and result resources; the browser frontend provides setup, active interview, history/replay/transcript, and results views; domain services remain provider-neutral and use injected deterministic seams.

## Numbers

| Value | Number | Source |
|---|---:|---|
| API version | 1 | Existing Phase 5 REST contract |
| Default retention | 14 days | Existing Phase 7 `DEFAULT_RETENTION_DAYS` |
| Resume limit | 5 MiB | Existing Phase 3 and Phase 7 contracts |
| Signaling payload limit | 64 KiB | Existing Phase 5 transport contract |
| Frontend routes | 4 | DESIGN-FRESH |
| Health endpoints | 2 | DESIGN-FRESH |

## Out of scope

- Real vendor credentials, hosted model calls, OCR, production WebRTC media servers, and browser automation.
- Choosing final commercial providers without deployment-specific benchmark evidence.
- A full design system or authentication UI; the frontend uses a local deterministic identity for development.

## Acceptance

- [x] Marker contract written before implementation.
- [x] Real FastAPI application exposes health and version behavior.
- [x] Browser frontend is runnable from its package manifest and exercises documented API boundaries.
- [x] Existing tests execute public behavior; no source-text or hardcoded-only assertions remain.
- [x] Complete offline mock interview test covers ingestion, retrieval, routing, live voice, transport, persistence, and evaluation.
- [x] Failure, reconnect, cancellation, partial-audio, authorization, retention, and rate-limit cases are executable.
- [x] Benchmark and privacy/security seams run without credentials or network.
- [x] README, PLAN, and AGENTS contain production decisions and exact commands.
- [x] Marker evidence and landmines are recorded.
