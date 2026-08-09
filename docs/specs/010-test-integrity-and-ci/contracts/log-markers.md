# Phase 10 marker contract

## Required markers

The Phase 10 executable gate must print these exact strings after the corresponding real checks complete:

- `[PHASE10] backend-tests-ok`
- `[PHASE10] backend-quality-ok`
- `[PHASE10] mock-interview-e2e-ok`
- `[PHASE10] frontend-tests-ok`
- `[PHASE10] frontend-build-ok`
- `[PHASE10] coverage-enforced-ok`
- `[PHASE10] ci-config-ok`

Markers are evidence breadcrumbs only. The command must also return a non-zero exit code for a failed or skipped required check.

## Forbidden failure patterns

Evidence and CI logs must not contain:

- `Traceback`
- `Script Error`
- `secret leaked`
- `cross-owner data returned`
- `TODO: production`
- `NotImplementedError`
- `placeholder CI`
- `tests passed (placeholder)`
- `linting passed (placeholder)`
- `type checks passed (placeholder)`
- `skipped required check`
- raw provider keys, Firebase credentials, or bearer tokens
