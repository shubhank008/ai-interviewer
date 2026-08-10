# Plan 014 - Full user E2E acceptance

## Global Constraints

- Preserve capability interfaces and abstract-first provider routing; candidate and interviewer providers must remain independently injectable.
- Keep default tests offline, deterministic, CPU-only, credential-free, and free of heavyweight model downloads or external network calls.
- Exercise real application/domain behavior rather than source inspection, printed markers alone, mocks, or expected-string substitution.
- Keep media frames on the WebRTC/media seam and control, transcript, and state events on WebSocket.
- Preserve owner authorization, retention, deletion, transcript finality, evaluation-after-completion, stale-response rejection, cancellation, timeout, fallback, and timestamp ordering.
- Keep local and configured runtime profiles explicit. Missing Firebase/provider configuration must produce an honest skip, not a local pass mislabeled as production readiness.
- Redact credentials, personal data, and private provider responses from diagnostics and artifacts.
- Visual claims require browser frames from the running API/frontend; artifacts belong outside version control.
- Use focused semantic commits and do not push or open a pull request from this branch.
- Update `AGENTS.md` only when a durable landmine is discovered.

## Marker contract

Written in `contracts/log-markers.md` before implementation.

- Requires: `[PHASE14] auth-setup-ok`, `[PHASE14] pdf-rag-ok`, `[PHASE14] providers-separated-ok`, `[PHASE14] browser-media-loop-ok`, `[PHASE14] interruption-reconnect-ok`, `[PHASE14] persisted-evaluation-ok`, `[PHASE14] replay-deletion-ok`, `[PHASE14] negative-journeys-ok`, `[PHASE14] configured-integrations-report-ok`, `[PHASE14] evidence-artifacts-ok`
- Forbids: `Traceback`, `Script Error`, `secret leaked`, `Firebase private key`, `media tunneled over websocket`, `stale response spoken`, `NotImplementedError`, `placeholder`, `skipped required check`, `EXPECTED_STRING_SUBSTITUTION`

## Work order

1. `docs/specs/014-full-user-e2e-acceptance/` - record user behavior, constraints, markers, and evidence.
2. `src/interviewer_domain/e2e_acceptance.py` - compose the real local acceptance journey, artifact schema, provider metadata, negative journeys, and configured skip reporting.
3. `tests/test_phase14_full_user_e2e.py` and `scripts/test_phase14.sh` - execute the positive and negative behavior paths and assert markers and forbidden patterns.
4. `src/interviewer_api/app.py` and existing domain seams - make only minimal boundary changes required for upload/session/completion/artifact assertions.
5. `README.md`, `SPEC.md`, `PLAN.md`, and operational documentation - explain commands, artifact locations, configured-provider limits, and honest evidence.
6. Run lint/typecheck, backend/frontend gates, mock turn, Phase 13, Phase 14, and browser evidence checks.
7. Inspect worktree and create focused semantic commits for specification, plan/contract, implementation, tests/evidence, and docs.

## Test plan

- Unit: acceptance artifact serialization, provider separation, redaction, configured skip detection, and negative journey diagnostics.
- Integration: real local parser, retrieval, provider interfaces, live voice, WebRTC media buffer, WebSocket state, persistence, evaluation, replay/history, and deletion.
- e2e: `scripts/test_phase14.sh` prints every required marker and rejects forbidden patterns.
- Configured: opt-in only, tagged by environment, using injected transports/backends and redacted provider/model/region/timing/cost metadata.
- Frames: run the API and frontend, use browser tooling for setup, live controls/connection, transcript/events, and results or an honest unavailable-provider state; save frames under `.agent_tmp/phase14-evidence/`.
