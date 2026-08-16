# Plan 017 - Live document parsing and adaptive interview ending

## Global Constraints

- Capability interfaces precede concrete adapters; domain code remains provider-neutral.
- OpenRouter credentials and model settings are environment-injected and never emitted in evidence.
- `DOCUMENT_LLM_MODEL` must remain separate from `LLM_MODEL`; diagnostics report presence and model metadata only.
- Resume and job-description data are untrusted, bounded, owner-scoped sensitive data.
- Local parsing remains an explicit deterministic/development path; configured live providers must be exercised or reported failed.
- Phase 16 uses programmatic Interviewer Agent and Interviewee Agent audio buffers; no browser or media bytes in control events.
- Session completion occurs only after the current candidate transcript is persisted and the end reason is emitted.
- Existing deterministic providers and compatibility modules must continue to pass.

## Work order

1. Extend the document capability contract and models for structured, safe parser results without coupling domain code to OpenRouter.
2. Implement an injected vision-document OpenRouter adapter with a dedicated prompt, strict JSON validation, bounds, redaction-safe metadata, and explicit local fallback composition.
3. Add `DOCUMENT_LLM_MODEL` configuration, diagnostics, readiness metadata, environment template documentation, and adapter tests.
4. Add structured end-decision models and planner validation, then enforce adaptive ending and hard limits in the session engine with an injectable clock.
5. Update the rehearsal orchestration to share the policy and produce end-reason and trigger evidence for both journeys.
6. Run focused tests, full backend gates, lint/typecheck, and mock-turn verification; update roadmap and invariants if needed.

## Files expected to change

- `src/interviewer_domain/models.py`
- `src/interviewer_domain/capabilities/contracts.py`
- `src/interviewer_domain/documents.py`
- `src/interviewer_domain/adapters/voice.py` or a dedicated document adapter module
- `src/interviewer_domain/adapters/integrations.py`
- `src/interviewer_domain/configuration.py`
- `src/interviewer_domain/session.py`
- `src/interviewer_domain/phase16_rehearsal.py`
- `src/interviewer_domain/__init__.py`
- `.env.example`, `PLAN.md`, and `docs/specs/017-live-document-and-adaptive-ending/contracts/log-markers.md`
- Focused tests for adapters, configuration, session ending, and rehearsal parity
