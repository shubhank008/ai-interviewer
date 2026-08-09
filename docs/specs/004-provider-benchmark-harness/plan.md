# Plan 004 - Provider Implementations and Benchmark Harness

## Global Constraints

- Preserve capability-based architecture; vendor names stay inside adapters and configuration.
- Implement normalized interfaces and shared operational behavior before concrete integrations.
- Keep local execution CPU-only and deterministic; tests must not need network, secrets, model downloads, or optional packages.
- Every concrete provider gets unit coverage through real adapter code with injected fakes rather than mocks.
- Provider failures, cancellation, timeout, and unavailable dependencies use `ProviderError` and `HealthStatus`.
- Benchmark data must not contain secrets or user documents and must distinguish fixture quality from measured provider quality.
- Do not commit, push, or create a pull request for this task.

## Marker contract

Written in `contracts/log-markers.md` before implementation. The evidence run must print:

- `[BENCHMARK] provider-adapters-ok`
- `[BENCHMARK] health-capabilities-ok`
- `[BENCHMARK] fallback-routing-ok`
- `[BENCHMARK] deterministic-report-ok`
- `[BENCHMARK] metrics-complete-ok`

Forbidden patterns include `Traceback`, `AssertionError`, `Script Error`, `TypeError`, and `TimeoutError`.

## Work order

1. Extend normalized measurement and provider contracts with quality, cost, resource, first-byte, and end-to-end fields.
2. Add provider-independent adapter seams and optional Faster-Whisper, Piper/Kokoro, and OpenRouter implementations.
3. Add generic fallback routing and configuration feature flags without coupling session logic to vendors.
4. Add deterministic benchmark runner and report serialization.
5. Add unit tests for every concrete class and a real benchmark integration path.
6. Update exports, PLAN.md, README.md, and AGENTS.md.

## Test plan

- Unit: adapter request validation, injected backend translation, optional dependency health, cancellation, and normalized errors.
- Unit: fallback selection, capability discovery, and feature flags.
- e2e: deterministic providers run through the real turn-shaped benchmark runner and print all markers.
- Frames: none, this feature has no visual surface.
- Validation: `python -m unittest discover -s tests -v`, markdown lint where available, compileall, and static checks available in the repository.
