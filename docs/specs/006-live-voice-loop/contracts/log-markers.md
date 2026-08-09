# Phase 6 marker contract

The deterministic Phase 6 test run must print each required marker exactly once or more. Markers are evidence of behavior, not substitutes for assertions.

## Required markers

- `[LIVE] incremental STT connected`
- `[LIVE] cancellable response streamed`
- `[LIVE] stale prefetch rejected`
- `[LIVE] audio chunks ordered`
- `[LIVE] interruption stopped playback`
- `[LIVE] artifacts timestamped`
- `[LIVE] latency measured`
- `[LIVE] provider fallback emitted`
- `[LIVE] mock turn complete`

## Forbidden patterns

The run must not print any of the following:

- `Script Error`
- `Traceback`
- `AssertionError`
- `stale response spoken`
- `media tunneled over websocket`
