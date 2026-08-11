# Phase 16 marker contract: Live Beta Enablement

## Required markers

- `[BETA16] composition-production-ok`
- `[BETA16] firebase-auth-owner-isolation-ok`
- `[BETA16] firestore-session-lifecycle-ok`
- `[BETA16] storage-firebase-lifecycle-ok`
- `[BETA16] storage-local-lifecycle-ok`
- `[BETA16] resume-rag-context-ok`
- `[BETA16] webrtc-microphone-track-ok`
- `[BETA16] stt-partial-final-timestamps-ok`
- `[BETA16] llm-interviewer-stream-ok`
- `[BETA16] kokoro-audio-playback-ok`
- `[BETA16] transcript-recording-persisted-ok`
- `[BETA16] llm-evaluation-score-ok`
- `[BETA16] retention-deletion-ok`
- `[BETA16] browser-recruiter-journey-ok`
- `[BETA16] browser-technical-journey-ok`
- `[BETA16] beta-evidence-redacted-ok`

## Forbidden output

No marker runner or evidence may contain `Traceback`, `Script Error`, API keys, bearer tokens, private keys, Firebase credentials, resume text, transcript text, audio bytes, raw provider payloads, or personal data. No deterministic provider may be reported as a real beta provider. Missing configuration must be `skipped`, and a selected provider failure must be `failed`.
