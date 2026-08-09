# Plan 011 - Runtime configuration and provider readiness

## Global Constraints

- Follow the SDD lifecycle and keep focused semantic commits.
- Preserve capability interfaces and keep vendor imports, credentials, network calls, and heavyweight models outside default offline tests.
- Keep local deterministic providers separate from production claims and require explicit production configuration.
- Never print secrets, bearer tokens, API keys, Firebase private values, user data, or provider request payloads in diagnostics.
- Preserve the Phase 5 media/control boundary and Phase 6 cancellation, ordering, transcript, and fallback behavior.
- Preserve Phase 7 owner checks, 5 MB PDF upload validation, 14-day retention metadata, complete deletion, and rate limits.
- Keep benchmark results as measurement seams; configured provider readiness requires integration evidence.
- Update `AGENTS.md` only if implementation reveals a durable landmine.

## Marker contract

Written before implementation in `contracts/log-markers.md`.

- Requires: `[PHASE11] config-local-ok`, `[PHASE11] config-production-fail-safe`, `[PHASE11] provider-health-capabilities-ok`, `[PHASE11] provider-fallback-e2e-ok`, `[PHASE11] mock-runtime-e2e-ok`, `[PHASE11] diagnostics-redacted`
- Forbids: `Traceback`, `Script Error`, `secret leaked`, `raw provider key`, `Firebase private key`, `Bearer dev-token`, `NotImplementedError`, `TODO: production`, `placeholder`, `skipped required check`

## Work order

1. `docs/specs/011-runtime-configuration-and-provider-readiness/` - record user behavior, constraints, markers, and evidence requirements.
2. `.env.example` - document safe runtime variables without secret values.
3. `src/interviewer_domain/configuration.py` - add typed settings, profile validation, redacted diagnostics, provider readiness checks, and composition seams.
4. `src/interviewer_domain/__init__.py` - expose public configuration contracts.
5. `src/interviewer_api/app.py` - compose the local profile through configuration and expose safe readiness health behavior without weakening local operation.
6. `tests/test_configuration.py` and `tests/test_phase11_runtime.py` - cover real configuration, adapters, readiness, fallback, diagnostics, and mock turn-shaped execution.
7. `README.md`, `docs/provider-readiness.md`, `SPEC.md`, `PLAN.md`, and scripts - document profiles, provider characteristics, markers, and gate commands.
8. Run focused checks, all required gates, inspect logs for forbidden patterns, and commit focused semantic slices.

## Test plan

- Unit: typed environment parsing, profile validation, secret redaction, capability requirements, health aggregation, provider-shaped adapter factories, and fallback behavior.
- Contract: local and production configuration composition satisfies existing STT, TTS, LLM, and fallback interfaces.
- E2E: run a real mock turn with configured local/fallback provider instances and assert transcript, response, audio, and all Phase 11 markers.
- Operational: verify missing production requirements fail before readiness, while local defaults never require credentials or network access.
- Frames: none; this phase has no visual change.
