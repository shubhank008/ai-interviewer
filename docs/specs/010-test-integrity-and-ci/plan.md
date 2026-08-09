# Plan 010 - Test integrity and real CI gates

## Global Constraints

- Follow the SDD lifecycle and keep focused semantic commits.
- Preserve capability interfaces and keep third-party imports, credentials, network calls, and heavyweight models outside the default offline suite.
- Do not turn deterministic fixtures into claims about production provider readiness.
- Tests must call real public behavior and assert observable outputs, state, persistence, transport, or failure behavior; do not inspect source text.
- Keep frontend visual code separate from backend and transport behavior.
- Do not commit secrets, `.env` files, generated coverage, browser artifacts, `node_modules`, or build output.
- Keep the Phase 5 media/control separation and Phase 6 cancellation, ordering, and transcript invariants.
- Preserve Phase 7 owner checks, retention, deletion, upload bounds, and rate limits.
- Preserve Phase 8 completed-interview and final-candidate-transcript evaluation rules.
- Update AGENTS.md with any durable testing or CI landmine discovered during implementation.

## Marker contract

Write `contracts/log-markers.md` before implementation. Markers must prove executed checks and must not be used as substitutes for assertions or CI exit codes.

## Work order

1. Measure the current test and build surface and audit tests for source inspection or static-only assertions.
2. Add reproducible development-tool manifests and explicit backend/frontend commands.
3. Make `scripts/lint_and_typecheck.sh` strict: missing tools, lint errors, type errors, compile errors, and build errors fail.
4. Add a backend test command that runs the full unittest suite and the Phase 9 mock evidence path.
5. Add frontend lint, type-check, unit/component test, and production-build commands; use a minimal testable application seam before adding UI tests.
6. Add coverage collection and initial per-surface thresholds after measuring the baseline. Keep thresholds explicit and documented.
7. Replace `.github/workflows/ci.yml` placeholder steps with real setup, dependency caching, backend checks, frontend checks, offline evidence, coverage, and report artifacts.
8. Add CI guards proving secrets are absent from the offline job and that skipped commands fail the job.
9. Update README, PLAN.md, and SPEC.md with the commands, tier boundaries, and coverage policy.
10. Run the full local gate, inspect generated artifacts and git status, and commit focused semantic slices.

## Test plan

### Audit

- Search tests for source reads, `inspect.getsource`, source-text assertions, unconditional success, and tests that never call the behavior under test.
- Confirm existing tests exercise domain methods, adapters, ASGI routes, persistence, transport, and evaluation through real imports.

### Backend

- Run all backend unit and contract tests.
- Run the complete offline Phase 9 mock interview pipeline.
- Exercise compile, lint, type checking, failure behavior, owner isolation, retention, cancellation, and provider fallback.

### Frontend

- Install from the committed lockfile in a clean environment.
- Run formatting/lint/type checks, component tests, and production build.
- Keep browser voice tests out of this phase; Phase 13 and Phase 14 own them.

### CI

- Run the workflow on pull requests and pushes to `main`.
- Verify failures for a deliberately broken lint/type/test/build command in a disposable check or fixture.
- Verify coverage reports are generated and thresholds are enforced.
- Verify offline jobs run without provider secrets or network access.

## Definition of done

- The workflow executes real checks rather than echoing success.
- Local commands and CI commands are the same or use the same scripts.
- Required tools are pinned and missing tools cannot be silently skipped.
- Backend and frontend reports are uploaded by CI without sensitive values.
- Coverage thresholds are explicit and enforced.
- Existing tests are behavior-level tests, with any intentionally deterministic fixture documented.
- README, PLAN.md, SPEC.md, and AGENTS.md are consistent with the implementation.
