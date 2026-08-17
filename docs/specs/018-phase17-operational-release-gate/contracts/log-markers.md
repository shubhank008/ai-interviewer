# Phase 17 marker contract

## Required markers

- `[RELEASE17] evidence-written`
- `[RELEASE17] docker-compose-definition-ok`
- `[RELEASE17] production-fails-closed-ok`
- `[RELEASE17] backend-quality-ok`
- `[RELEASE17] backend-tests-ok`
- `[RELEASE17] mock-interview-e2e-ok`
- `[RELEASE17] frontend-quality-ok`
- `[RELEASE17] frontend-tests-ok`
- `[RELEASE17] frontend-build-ok`
- `[RELEASE17] launch-blockers-recorded`

## Failure patterns

Evidence and logs must not contain `LLM_API_KEY`, `OPENROUTER_API_KEY`, `Authorization`, `Bearer `, private key material, raw resume text, transcript text, audio bytes, or raw provider payloads.

The command must exit nonzero when any required deterministic check fails or any documented live-launch blocker remains.
