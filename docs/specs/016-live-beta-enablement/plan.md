# Plan 016 - Live Beta Enablement

## Global Constraints

- Abstract interfaces precede concrete adapters and business logic remains vendor-neutral.
- The explicit beta provider set is Firebase Auth, EU Firestore, Firebase Storage selected by `STORAGE_BACKEND=gcs` plus local checks, OpenRouter, WhisperX small/small.en on CPU, Kokoro 0.9.4 English, timestamped agent audio buffers, and an OpenRouter-based evaluator.
- CPU-only workers are required; no model downloads happen automatically.
- Phase 16 is live-mandatory. Live provider and agent-to-agent rehearsal tests are the only release evidence. Offline tests protect contracts only and cannot justify stopping implementation or pass beta readiness.
- Delegated implementation must complete configured provider execution and agent-to-agent acceptance. It may stop only for a genuine external authorization, security, or infrastructure blocker that is recorded precisely.
- Never log or store credentials, raw provider payloads, resume text, transcript text, or audio in evidence.
- Preserve owner isolation, 10 MB job-description and resume limits, 14-day resume retention, 7-day combined-audio retention, 30-day audit/access retention, deletion, cancellation, retries, timeouts, and redacted readiness.
- Phase 16 live rehearsal uses timestamped in-memory audio buffers between Interviewer and Interviewee agents; browser URL, browser automation, WebRTC, and TURN are deferred. Media bytes never enter control events.

## Work order

1. Keep capability boundaries provider-neutral while treating live execution, not offline execution, as the release gate.
2. Implement the production composition root for Firebase Auth, Firestore, Firebase Storage selected by `STORAGE_BACKEND=gcs`, WhisperX small, OpenRouter, and Kokoro; reject accidental in-memory services in production.
3. Implement Firebase Web Auth email/password and Google Sign-In signup/login, open signup, session restoration, and Firebase Admin token verification.
4. Implement Firestore repositories for owner-scoped sessions, events, transcripts, evaluations, users, deletion state, and 30-day audit/access records.
5. Implement Firebase Storage artifact repositories with upload, download, replay, retention, partial-failure, and deletion verification; retain local storage only for development and deterministic checks. Do not add S3.
6. Implement 10 MB job-description/resume validation, password-protected PDF errors, text-only PDF parsing with graceful scanned/encrypted failure, source-linked retrieval, LLM context injection, and deletion.
7. Keep browser microphone, browser URL, browser automation, WebRTC, STUN, and TURN outside Phase 16 acceptance; the live rehearsal uses timestamped buffers exchanged by the two agents.
8. Implement WhisperX `small` chunked transcription and CPU worker lifecycle, plus a provider/model benchmark matrix using fixture audio and Kokoro-generated test audio.
9. Implement OpenRouter streaming structured interviewer responses and evaluation with the configured model, 60-second timeout, three retries, permanent-error classification, and redacted token/time/cost metrics.
10. Implement Kokoro English synthesis with random per-invocation voice selection, browser-compatible audio normalization, playback sequencing, interruption, and cancellation.
11. Connect the browser frontend to Firebase Auth, upload, microphone capture, WebSocket, selected audio transport, transcript, replay, results, consent, and deletion paths.
12. Implement the full live Phase 16 rehearsal runner. It must execute provider-tagged operations, both recruiter and technical agent-to-agent journeys, storage switching, negative cases, retention/deletion, and redacted evidence for every marker.
13. Benchmark the single Docker container first on self-hosted and Railway profiles. Keep separate API/model/audio/evaluation containers as a roadmap item for later scaling.

## Test plan

- Live provider tests for every selected adapter and failure mode are the release gate.
- Agent-to-agent live E2E tests cover Firebase-authenticated ownership, setup, resume/job fixtures, recruiter and technical interview turns, audio buffers, evaluation, replay, retention, and deletion. Browser tests are deferred from Phase 16.
- Storage tests cover Firebase Storage bucket `gs://the-interviewer-c3a01.firebasestorage.app` via `STORAGE_BACKEND=gcs`; local storage remains a separate development/deterministic check. FTP is deferred.
- Resume tests use `tests/demo_resume.pdf` and `tests/demo_jobdescription.txt`, plus protected/scanned PDF cases.
- Benchmark tables report STT/TTS/LLM provider, model, version, device, latency, CPU, memory, tokens, cost, quality, failures, and limitations without sensitive payloads.
- Evidence must distinguish exercised, skipped, and failed; skipped never passes beta readiness.
- Offline gates are optional contract protection only. Run configured live beta gates and save only redacted metadata and screenshots.
