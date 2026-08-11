# Plan 016 - Live Beta Enablement

## Global Constraints

- Abstract interfaces precede concrete adapters and business logic remains vendor-neutral.
- The explicit beta provider set is Firebase Auth, Firestore, Firebase Storage or local filesystem, OpenRouter, Faster-Whisper, Kokoro, WebRTC, and an OpenRouter-based evaluator.
- CPU-only workers are required; no model downloads happen automatically.
- Default tests remain deterministic and offline, but beta acceptance requires real configured execution.
- Never log or store credentials, raw provider payloads, resume text, transcript text, or audio in evidence.
- Preserve owner isolation, 5 MB PDF limit, 14-day retention, deletion, cancellation, retries, timeouts, and redacted readiness.
- Media bytes stay on WebRTC or storage and never enter WebSocket control events.

## Work order

1. Move protocols into `src/interviewer_domain/capabilities/`, adapters into `src/interviewer_domain/adapters/`, and deterministic implementations into `src/interviewer_domain/providers/in_memory/`; preserve compatibility exports during migration.
2. Implement a production composition root that wires the explicit beta provider set and rejects accidental in-memory services in production.
3. Implement Firebase Web Auth and Firebase Admin token verification with real protected frontend/API flow.
4. Implement Firestore repositories for sessions, events, transcripts, evaluations, users, and deletion state.
5. Implement Firebase Storage and local filesystem artifact repositories with a common lifecycle contract.
6. Implement resume upload, parsing, source-linked retrieval, and deletion through the live API.
7. Implement real WebRTC media ingress/egress, audio recording, signaling, and STUN/TURN configuration.
8. Implement Faster-Whisper streaming/chunked transcription and CPU worker lifecycle.
9. Implement OpenRouter streaming structured interviewer responses and LLM evaluation.
10. Implement Kokoro streaming/chunked synthesis, audio format normalization, playback sequencing, interruption, and cancellation.
11. Connect the browser frontend to real auth, upload, WebSocket, WebRTC, transcript, replay, results, and deletion paths.
12. Add provider-tagged integration tests and a real-browser beta rehearsal with frame evidence.

## Test plan

- Contract tests for every capability and adapter with deterministic seams.
- Tagged live tests for each selected provider and failure mode.
- Full browser test from Firebase signup through deletion using real microphone and audio playback.
- Evidence must distinguish exercised, skipped, and failed; skipped never passes beta readiness.
- Run offline gates plus configured beta gates. Save only redacted metadata and screenshots.
