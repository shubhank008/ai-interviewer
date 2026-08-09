# Marker Contract - Persistence, user identity, and user experience

The deterministic persistence test is the evidence harness for this feature. It
must print each required marker exactly once when the behavior passes.

## Required markers

```text
[PERSISTENCE] auth-isolation-ok
[PERSISTENCE] adapters-ok
[PERSISTENCE] retention-deletion-ok
[PERSISTENCE] upload-rate-limit-ok
[PERSISTENCE] mock-persistence-ok
[PERSISTENCE] ux-contracts-ok
```

## Meaning

- `auth-isolation-ok`: authenticated identities can access only their own interview records and files.
- `adapters-ok`: Firebase Auth, Firestore, local filesystem, and S3-compatible adapters work through injected provider seams without cloud access.
- `retention-deletion-ok`: 14-day metadata enforcement and complete per-interview deletion remove all record and artifact categories.
- `upload-rate-limit-ok`: PDF and 5 MB validation plus deterministic request limiting reject unsafe or excessive requests.
- `mock-persistence-ok`: a real setup-to-history-to-transcript/replay/results persistence path succeeds with local seams.
- `ux-contracts-ok`: setup, active, history, replay, transcript, and results resource contracts serialize stable provider-neutral payloads.

## Forbidden output

The test output must not contain these failure patterns:

```text
Traceback
AssertionError
Script Error
TypeError
TimeoutError
```
