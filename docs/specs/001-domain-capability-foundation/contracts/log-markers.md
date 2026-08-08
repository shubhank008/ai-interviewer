# Marker Contract - Domain Capability Foundation

The deterministic mock-turn test is the evidence harness for this feature. It
must print each required marker exactly once when the foundation works.

## Required markers

```text
[FOUNDATION] domain-models-ok
[FOUNDATION] capabilities-ok
[FOUNDATION] mock-turn-ok
[FOUNDATION] lifecycle-ok
```

## Meaning

- `domain-models-ok`: normalized session, turn, transcript, recording,
  evaluation, and measurement values validate and serialize safely.
- `capabilities-ok`: all Phase 1 capability protocols are importable and the
  deterministic providers satisfy the contracts without vendor dependencies.
- `mock-turn-ok`: a real mock voice turn produces a final transcript, LLM
  response, and TTS audio through the capability boundaries.
- `lifecycle-ok`: ordered started, processing, completed lifecycle events are
  emitted and persisted by the in-memory event bus and data store.

## Forbidden output

The test output must not contain these failure patterns:

```text
Traceback
AssertionError
Script Error
TypeError
TimeoutError
```
