# Marker Contract - Voice-First Interview Engine

The deterministic state-machine test is the evidence harness for this feature. It
must print each required marker exactly once when the engine works.

## Required markers

```text
[ENGINE] recruiter-mode-ok
[ENGINE] technical-mode-ok
[ENGINE] lifecycle-ok
[ENGINE] guarded-planning-ok
[ENGINE] cancellation-failure-ok
[ENGINE] provider-failure-ok
[ENGINE] mock-session-ok
```

## Meaning

- `recruiter-mode-ok`: recruiter sessions select recruiter-specific opening and follow-up topics.
- `technical-mode-ok`: technical sessions select technical-specific opening and follow-up topics.
- `lifecycle-ok`: start, activation, turn processing, and terminal events are ordered and correlated.
- `guarded-planning-ok`: stale prepared follow-ups are rejected after a changed answer, while current plans remain usable.
- `cancellation-failure-ok`: cancellation transitions the session to cancelled without emitting a completion event.
- `provider-failure-ok`: provider failure transitions the session to failed without emitting a completion event.
- `mock-session-ok`: deterministic Phase 1 providers complete a real session turn and produce transcript and audio-shaped output.

## Forbidden output

The test output must not contain these failure patterns:

```text
Traceback
AssertionError
Script Error
TypeError
TimeoutError
```
