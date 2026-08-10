# Plan 015 - Opt-in provider integration suite

## Global Constraints

- Preserve capability interfaces, abstract-first routing, normalized errors, cancellation, streaming, fallback, and owner checks.
- Default tests remain offline, deterministic, CPU-only, credential-free, and free of model downloads or network calls.
- Keep provider wire formats, credentials, retries, timeouts, rate limits, redaction, data policy, and deletion inside adapters.
- Never put media bytes in WebSocket events; visual claims require browser frames.
- Do not expose secrets, user documents, transcript text, audio, private Firebase material, or raw provider payloads.
- Missing configured providers are explicit skips, not passes or readiness claims.
- Optional imports and heavyweight models remain outside module import and deterministic tests.
- Use focused semantic commits; do not push, open a PR, or run publication workflow.

## Marker contract

Written in `contracts/log-markers.md` before implementation. The runner must emit exact exercised, skipped, failed, capability, lifecycle, redaction, and browser-media markers and reject forbidden sensitive output.

## Work order

1. `src/interviewer_domain/provider_adapters.py` - add concrete local model and OpenRouter streaming transports with safe metadata, validation, timeouts, and cancellation.
2. `src/interviewer_domain/persistence.py` and new provider integration module - add Firebase, Firestore, and object-storage SDK transports behind existing protocols and safe configuration composition.
3. `src/interviewer_domain/provider_integration.py` - implement profile selection, redacted evidence, skip/fail semantics, negative cases, measurements, and markers.
4. `tests/test_provider_integration.py` and `scripts/test_phase15.sh` - behavior-level adapter tests and opt-in tagged execution.
5. `.env.example`, `README.md`, `SPEC.md`, `PLAN.md`, `docs/provider-readiness.md` - exact safe setup, limitations, and commands.
6. Run offline gates, Phase 14, and Phase 15 configured checks where safe; save evidence under `.agent_tmp/phase15-evidence/`.

## Test plan

- Unit/contract: concrete adapters with local transport seams, malformed payloads, cancellation, timeout, retry, redaction, and metadata validation.
- Opt-in integration: pytest markers `integration`, `provider`, and capability-specific markers; explicit environment/profile selection only.
- E2E: configured voice path through existing API, WebSocket, WebRTC/media, persistence, and evaluation boundaries where infrastructure permits.
- Frames: authenticated setup, readiness, live voice/media state, transcript/audio status, results, or an honest configured-provider failure screen.
