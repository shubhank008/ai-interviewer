# Phase 16 marker contract: Live Beta Enablement

## Required markers

- `[BETA16] composition-production-ok`
- `[BETA16] firebase-auth-owner-isolation-ok`
- `[BETA16] firestore-session-lifecycle-ok`
- `[BETA16] storage-firebase-lifecycle-ok`
- `[BETA16] storage-firebase-lifecycle-ok`
- `[BETA16] storage-local-lifecycle-ok`
- `[BETA16] resume-rag-context-ok`
- `[BETA16] agent-audio-transport-ok`
- `[BETA16] stt-partial-final-timestamps-ok`
- `[BETA16] llm-interviewer-stream-ok`
- `[BETA16] kokoro-audio-playback-ok`
- `[BETA16] transcript-recording-persisted-ok`
- `[BETA16] llm-evaluation-score-ok`
- `[BETA16] retention-deletion-ok`
- `[BETA16] agent-recruiter-journey-ok`
- `[BETA16] agent-technical-journey-ok`
- `[BETA16] beta-evidence-redacted-ok`

## Forbidden output

No marker runner or evidence may contain `Traceback`, `Script Error`, API keys, bearer tokens, private keys, Firebase credentials, resume text, transcript text, audio bytes, raw provider payloads, or personal data. No deterministic provider may be reported as a real beta provider. Missing configuration must be `skipped`, and a selected provider failure must be `failed`. Live evidence is required for readiness; offline tests cannot satisfy a marker. The runner must record redacted provider/model/version, device, latency, CPU, memory, token, cost, quality, failure, and limitation metadata. Permanent OpenRouter failures such as insufficient balance, invalid model, or HTTP 404 are failed without retry; transient requests use a 60-second timeout and at most three retries.
