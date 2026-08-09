# Phase 9 marker contract

## Required markers

The executable Phase 9 evidence test must print these exact strings after exercising real public behavior:

- `[PHASE9] api-health-ok`
- `[PHASE9] api-version-ok`
- `[PHASE9] mock-interview-e2e-ok`
- `[PHASE9] provider-fallback-ok`
- `[PHASE9] reconnect-ok`
- `[PHASE9] cancellation-ok`
- `[PHASE9] partial-audio-ok`
- `[PHASE9] authorization-retention-rate-limit-ok`
- `[PHASE9] benchmark-security-ok`
- `[PHASE9] frontend-build-ok`

## Forbidden failure patterns

Evidence must not contain:

- `Traceback`
- `Script Error`
- `secret leaked`
- `cross-owner data returned`
- `TODO: production`
- `NotImplementedError`
