# Phase 8 marker contract

The deterministic test harness must print these exact success markers:

- `[EVALUATION] rubric-quality-ok` - both mode rubrics normalize weights and stay bounded.
- `[EVALUATION] deterministic-ok` - identical completed input produces identical structured output.
- `[EVALUATION] mock-path-ok` - the real transcript/context/evaluator/persistence/results path succeeds offline.
- `[EVALUATION] access-retention-ok` - wrong-owner and expired-interview access is rejected.

The harness must not emit these failure patterns:

- `evaluation failed`
- `Traceback`
- `Script Error`
- `score=-`
- `score=101`
- `invented evidence`
