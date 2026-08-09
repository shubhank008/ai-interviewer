# Phase 11 marker contract

## Required markers

The Phase 11 executable evidence path must print these exact strings after the corresponding real behavior completes:

- `[PHASE11] config-local-ok`
- `[PHASE11] config-production-fail-safe`
- `[PHASE11] provider-health-capabilities-ok`
- `[PHASE11] provider-fallback-e2e-ok`
- `[PHASE11] mock-runtime-e2e-ok`
- `[PHASE11] diagnostics-redacted`

Markers are evidence breadcrumbs only. Assertions and non-zero exit codes remain authoritative.

## Forbidden failure patterns

Evidence and diagnostics must not contain:

- `Traceback`
- `Script Error`
- `secret leaked`
- `raw provider key`
- `Firebase private key`
- `Bearer dev-token`
- `NotImplementedError`
- `TODO: production`
- `placeholder`
- `skipped required check`
- API keys, private keys, bearer tokens, or user documents
