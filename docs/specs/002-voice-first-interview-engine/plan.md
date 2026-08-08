# Plan 002 - Voice-First Interview Engine

## Global Constraints

- Business logic remains provider-independent and must use Phase 1 capability interfaces.
- The product remains voice-first; text in this slice represents plans, transcripts, prompts, and events only.
- Recruiter and technical modes are explicit and must produce mode-appropriate plans without unsupported company or persona claims.
- Session and turn state transitions are explicit, deterministic, and reject invalid operations rather than silently repairing them.
- Lifecycle events are ordered per session, carry correlation identifiers, and never report completion after cancellation or failure.
- Prepared follow-ups are advisory only. A changed conversation context must invalidate stale preparation before a response is generated.
- Cancellation is cooperative through the existing normalized `CancellationToken`; provider failures transition the session and preserve the original normalized error.
- Deterministic tests must not depend on wall-clock timing, randomness, network access, credentials, or vendor SDKs.
- Audio, transcripts, job descriptions, resumes, and evaluations remain sensitive; this slice adds no persistence or new data exposure.
- Preserve repository conventions: English, no em-dashes, focused semantic commits, and documentation kept current.

## Marker contract

Written in `contracts/log-markers.md` before implementation. The deterministic state-machine test must print these exact markers:

- Requires: `[ENGINE] recruiter-mode-ok`
- Requires: `[ENGINE] technical-mode-ok`
- Requires: `[ENGINE] lifecycle-ok`
- Requires: `[ENGINE] guarded-planning-ok`
- Requires: `[ENGINE] cancellation-failure-ok`
- Requires: `[ENGINE] mock-session-ok`
- Forbids: `Traceback`, `AssertionError`, `Script Error`, `TypeError`, `TimeoutError`

## Work order

1. `docs/specs/002-voice-first-interview-engine/` - record scope, work order, and executable marker contract.
2. `src/interviewer_domain/models.py` - extend normalized session status, question-plan, and transition values only as needed.
3. `src/interviewer_domain/contracts.py` - extend event and session-facing contracts only where the engine needs them.
4. `src/interviewer_domain/session.py` - implement the provider-independent state machine, guarded planner, lifecycle sequencing, and failure/cancellation transitions.
5. `src/interviewer_domain/__init__.py` - export the public engine types.
6. `tests/test_session_engine.py` - behavior-driven unit tests plus deterministic provider-backed mock-session coverage and markers.
7. `PLAN.md`, `README.md` - mark the Phase 2 slice complete and describe the new deterministic validation path.

## Test plan

- Unit: Python `unittest` tests for both modes, lifecycle transitions, sequence guards, cancellation, provider failures, and stale follow-up invalidation.
- Mock e2e: run the real `InterviewSessionEngine` with Phase 1 in-memory STT, LLM, TTS, event bus, and datastore providers; assert ordered events and persisted transcript/audio-shaped output.
- Frames: none; this feature has no visual UI.
- Validation: run `python -m unittest discover -s tests -v`, `python -m compileall -q src tests`, and markdownlint on changed Markdown files when available. Report absent lint/typecheck/mock-turn scripts as environment constraints.
