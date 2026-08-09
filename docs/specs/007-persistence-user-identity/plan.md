# Plan 007 - Persistence, user identity, and user experience

## Global Constraints

- Business logic depends on capability protocols, never Firebase, Firestore, S3, or filesystem SDKs directly.
- Abstract AuthProvider, DataStore, and StorageProvider behavior is defined before concrete adapters.
- Firebase and remote storage imports, credentials, network calls, and SDK initialization stay outside module import and deterministic tests.
- Every record and opaque artifact is scoped to an authenticated user and interview; cross-user access must fail safely without leaking existence.
- The default retention period is 14 days and complete deletion includes metadata, documents, transcripts, recordings, evaluations, derived references, and external-cache references represented by the datastore.
- Resume uploads are untrusted PDF input and must be validated before persistence; no prompt or document text becomes an instruction.
- Deterministic tests use injected backends, local filesystem fixtures, clocks, and rate-limit state. No browser, cloud, credential, or network dependency is allowed.
- The repository has no frontend source tree, so this phase defines clean UI-independent setup, active, history, replay, transcript, and results contracts rather than inventing a React stack.
- Preserve Phase 1-6 transport and live-voice boundaries: media stays in StorageProvider, control events stay in event/data seams, and transcript partial/final ordering is preserved.
- Follow repository conventions: focused semantic commits, English, no em-dashes, documented methods, and durable surprises recorded in AGENTS.md.

## Marker contract

Written before implementation. The real persistence test must print:

- Requires: `[PERSISTENCE] auth-isolation-ok`
- Requires: `[PERSISTENCE] adapters-ok`
- Requires: `[PERSISTENCE] retention-deletion-ok`
- Requires: `[PERSISTENCE] upload-rate-limit-ok`
- Requires: `[PERSISTENCE] mock-persistence-ok`
- Requires: `[PERSISTENCE] ux-contracts-ok`
- Forbids: `Traceback`, `AssertionError`, `Script Error`, `TypeError`, `TimeoutError`

## Work order

1. `docs/specs/007-persistence-user-identity/` - record user-visible scope, constraints, and executable evidence contract.
2. `src/interviewer_domain/contracts.py` - extend normalized auth, persistence, storage, retention, and rate-limit protocols without vendor types.
3. `src/interviewer_domain/persistence.py` - implement identity, authorization, retention, upload, rate-limit, UI resource contracts, local filesystem, Firebase/Firestore, and S3-compatible adapters using injected seams.
4. `src/interviewer_domain/providers.py` and `src/interviewer_domain/__init__.py` - preserve and expose deterministic persistence paths.
5. `tests/test_persistence.py` - cover each concrete adapter, isolation, complete deletion, expiry, upload validation, rate limiting, and real mock persistence path with markers.
6. `PLAN.md`, `README.md`, `AGENTS.md` - mark Phase 7 status, document API/domain UX contracts, and record any durable landmine.

## Test plan

- Unit: auth identity verification, ownership policy, upload validation, retention clock, token-bucket/window rate limit, local filesystem safety, and injected Firebase/Firestore/S3 adapter behavior.
- Mock e2e: create an authenticated interview, persist metadata plus transcript, recording, document, and evaluation through the real persistence service, then list, retrieve, enforce ownership, expire, and delete it.
- Frames: none. No frontend tree exists; UI-independent resource contracts are verified instead.
- Validation: `python -m unittest discover -s tests -v`, `python -m compileall -q src tests`, and markdownlint when available.
