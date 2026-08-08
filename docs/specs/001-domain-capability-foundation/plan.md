# Plan 001 - Domain Capability Foundation

## Global Constraints

- Interfaces are capability-based; business logic must not import vendor SDKs.
- The product interaction remains voice-first. Text is limited to setup,
  transcript, control, and result representations.
- Abstract capability contracts are defined before deterministic providers.
- Domain payloads are normalized and provider-specific formats stay behind
  adapters.
- Providers must support cancellation, timeout, normalized errors, health, and
  capability discovery where relevant.
- Audio, transcript, resume, job-description, and evaluation data are sensitive;
  this slice must not add secrets or weaken future data boundaries.
- Local deterministic providers are preferred for tests and must not depend on
  network access, clocks, randomness, or external credentials.
- Follow repository conventions: English, no em-dashes, focused changes, and
  documentation kept current.

## Marker contract

Written in `contracts/log-markers.md` before implementation. The mock-turn test
must print these exact markers:

- Requires: `[FOUNDATION] domain-models-ok`
- Requires: `[FOUNDATION] capabilities-ok`
- Requires: `[FOUNDATION] mock-turn-ok`
- Requires: `[FOUNDATION] lifecycle-ok`
- Forbids: `Traceback`, `AssertionError`, `Script Error`, `TypeError`, `TimeoutError`

## Work order

1. `docs/specs/001-domain-capability-foundation/` - record the feature scope,
   implementation order, and executable marker contract.
2. `src/interviewer_domain/models.py` - add immutable normalized domain values
   for sessions, turns, events, transcript, recordings, evaluation, and
   provider measurements.
3. `src/interviewer_domain/contracts.py` - define capability protocols and
   shared result, lifecycle, cancellation, health, capability, and error types.
4. `src/interviewer_domain/providers.py` - implement deterministic in-memory
   STT, LLM, TTS, data store, storage, and event bus providers.
5. `src/interviewer_domain/turn.py` - compose only the capabilities needed for a
   deterministic voice-shaped mock turn and emit lifecycle events.
6. `tests/test_foundation.py` - test model validation, contract behavior,
   normalized errors, provider behavior, ordering, cancellation, and a mock
   turn through real implementations.
7. `PLAN.md` and `README.md` - update status and describe the new package and
   validation commands if implementation is complete.

## Test plan

- Unit: Python `unittest` tests for domain invariants, provider contracts,
  deterministic outputs, event ordering, cancellation, and lifecycle failures.
- E2E/mock: execute the real `MockTurnRunner` with in-memory STT, LLM, TTS,
  event bus, and data store providers; assert transcript, response, audio, and
  lifecycle state, while printing all required markers.
- Frames: none; this feature has no visual UI.
- Validation: run `python -m unittest discover -s tests -v` and markdownlint on
  the changed Markdown files. No repository lint/typecheck script currently
  exists, so that absence is reported as a blocker.
