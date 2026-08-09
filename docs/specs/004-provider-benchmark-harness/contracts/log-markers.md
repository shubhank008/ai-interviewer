# Phase 4 marker contract

The deterministic benchmark evidence test must print these exact markers:

- `[BENCHMARK] provider-adapters-ok`
- `[BENCHMARK] health-capabilities-ok`
- `[BENCHMARK] fallback-routing-ok`
- `[BENCHMARK] deterministic-report-ok`
- `[BENCHMARK] metrics-complete-ok`

The evidence run must not print these failure patterns:

- `Traceback`
- `AssertionError`
- `Script Error`
- `TypeError`
- `TimeoutError`
