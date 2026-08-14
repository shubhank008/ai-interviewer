# Plan 016 - Live Beta Enablement

## Global Constraints

- Abstract interfaces precede concrete adapters and business logic remains vendor-neutral.
- The explicit beta provider set is Firebase Auth, Firestore, local/FTP/Firebase Storage, OpenRouter, WhisperX small, Kokoro, a benchmark-selected browser audio transport, and an OpenRouter-based evaluator.
- CPU-only workers are required; no model downloads happen automatically.
- Live tests are the only Phase 16 release evidence. Offline tests may protect contracts but cannot pass beta readiness.
- Never log or store credentials, raw provider payloads, resume text, transcript text, or audio in evidence.
- Preserve owner isolation, 10 MB job-description and resume limits, 14-day resume retention, 7-day combined-audio retention, 30-day audit/access retention, deletion, cancellation, retries, timeouts, and redacted readiness.
- Browser audio uses the simplest reliable timestamped chunk, VAD, streaming-Whisper, or WebRTC transport selected by benchmark evidence; media bytes never enter WebSocket control events.

## Work order

1. Keep capability boundaries provider-neutral while treating live execution, not offline execution, as the release gate.
2. Implement the production composition root for Firebase Auth, Firestore, local/FTP/Firebase Storage, WhisperX small, OpenRouter, and Kokoro; reject accidental in-memory services in production.
3. Implement Firebase Web Auth passwordless email-link signup/login, open signup, session restoration, and Firebase Admin token verification.
4. Implement Firestore repositories for owner-scoped sessions, events, transcripts, evaluations, users, deletion state, and 30-day audit/access records.
5. Implement local/NFS-compatible, FTP, and Firebase Storage artifact repositories with upload, download, replay, retention, partial-failure, and deletion verification. Do not add S3/GCS in this phase.
6. Implement 10 MB job-description/resume validation, password-protected PDF UI errors, text PDF parsing, scanned-PDF extraction through an explicit OCR/LLM adapter, source-linked retrieval, LLM context injection, and deletion.
7. Implement the simplest benchmark-selected browser microphone transport, initially timestamped chunks with a VAD or streaming-Whisper evaluation seam; defer custom WebRTC/TURN unless evidence selects it.
8. Implement WhisperX `small` chunked transcription and CPU worker lifecycle, plus a provider/model benchmark matrix using fixture audio and Kokoro-generated test audio.
9. Implement OpenRouter streaming structured interviewer responses and evaluation with the configured model, 60-second timeout, three retries, permanent-error classification, and redacted token/time/cost metrics.
10. Implement Kokoro English synthesis with random per-invocation voice selection, browser-compatible audio normalization, playback sequencing, interruption, and cancellation.
11. Connect the browser frontend to Firebase Auth, upload, microphone capture, WebSocket, selected audio transport, transcript, replay, results, consent, and deletion paths.
12. Implement the full live Phase 16 rehearsal runner. It must execute provider-tagged operations, both recruiter and technical browser journeys, storage switching, negative cases, retention/deletion, and redacted evidence for every marker.
13. Benchmark the single Docker container first on self-hosted and Railway profiles. Keep separate API/model/audio/evaluation containers as a roadmap item for later scaling.

## Test plan

- Live provider tests for every selected adapter and failure mode are the release gate.
- Full browser tests cover passwordless Firebase signup through deletion using real microphone capture and audio playback.
- Storage tests switch between local/FTP and Firebase Storage.
- Resume tests use `tests/resume_demo.pdf` and `tests/job_description.txt`, plus protected/scanned PDF cases.
- Benchmark tables report STT/TTS/LLM provider, model, version, device, latency, CPU, memory, tokens, cost, quality, failures, and limitations without sensitive payloads.
- Evidence must distinguish exercised, skipped, and failed; skipped never passes beta readiness.
- Offline gates are optional contract protection only. Run configured live beta gates and save only redacted metadata and screenshots.
