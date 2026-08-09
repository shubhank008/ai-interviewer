# Plan 009 - Production hardening

## Global Constraints

- Follow the SDD lifecycle and keep focused semantic commits.
- Capability interfaces precede integrations; third-party imports and network calls stay outside deterministic tests.
- Preserve Phase 5 media/control separation and Phase 6 async cancellation, ordered audio, and transcript rules.
- Preserve Phase 7 owner checks, 14-day retention, deletion, upload bounds, and rate limits.
- Preserve Phase 8 completed-interview and final-candidate-transcript evaluation rules.
- Do not add credentials, browser automation, heavyweight models, or network dependencies to the offline gate.
- Update AGENTS with any new production boundary or landmine before completion.

## Marker contract

Written before implementation in `contracts/log-markers.md`. Required markers prove real behavior, not source text. Failure patterns include `Traceback`, `Script Error`, `secret leaked`, and `cross-owner data returned`.

## Work order

1. Add `src/interviewer_api/` FastAPI application, dependency composition, and versioned resource routes.
2. Add deterministic API tests using the real ASGI application and injected in-memory services.
3. Add a focused complete-pipeline test and operational hardening cases using public domain interfaces.
4. Add frontend source, package manifest, build configuration, and a maintainable four-view flow.
5. Add Docker/local runtime files and scripts for install, test, lint, typecheck, and mock evidence.
6. Update README, PLAN, AGENTS, and marker evidence.
7. Run backend/frontend checks, compile/type checks, inspect status, and commit focused semantic slices.
8. Run `/no-mistakes`; never push or create a PR manually.

## Test plan

- Unit: API schemas/routes, security headers and authorization, benchmark seam, and frontend build.
- E2E: real domain pipeline from document ingestion and retrieval through routed live voice, transport, persistence, and evaluation.
- Resilience: provider failure/fallback, reconnect replay, cancellation, partial audio ordering, retention, owner isolation, and rate limit.
- Evidence: test output contains every required marker; frontend build artifact and API route smoke test prove runnable behavior.
