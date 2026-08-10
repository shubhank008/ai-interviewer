# Phase 15 marker contract

## Required markers

The Phase 15 runner emits these exact markers for each selected integration:

- `[PHASE15] profile-selected`
- `[PHASE15] integration-exercised`
- `[PHASE15] integration-skipped`
- `[PHASE15] integration-failed`
- `[PHASE15] auth-claims-owner-isolation-ok`
- `[PHASE15] storage-lifecycle-ok`
- `[PHASE15] document-artifact-ok`
- `[PHASE15] stt-results-ok`
- `[PHASE15] tts-audio-ok`
- `[PHASE15] llm-streaming-ok`
- `[PHASE15] fallback-retry-timeout-ok`
- `[PHASE15] deletion-ok`
- `[PHASE15] evidence-redacted-ok`
- `[PHASE15] browser-media-status-ok`

A selected profile prints `integration-exercised` only after a real configured provider path completes. An unavailable profile prints `integration-skipped` with a precise redacted reason. Failures print `integration-failed` and cause the selected integration gate to fail.

## Forbidden output

The runner and evidence must never contain `Traceback`, `Script Error`, `api_key`, `Authorization`, `Bearer `, private key material, Firebase credentials, resume text, transcript text, audio bytes, raw provider payloads, or personal data. It must not claim production readiness for skipped integrations or use an in-memory provider as an implicit fallback.
