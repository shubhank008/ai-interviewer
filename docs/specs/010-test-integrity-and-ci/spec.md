# Spec 010 - Test integrity and real CI gates

## What the feature is about and what the user experiences

Contributors receive trustworthy, reproducible validation before changes are merged. A clean checkout installs the documented tools, runs the backend and frontend checks, executes the offline mock interview evidence path, produces coverage reports, and fails when a required check is missing, skipped, or broken. The repository no longer reports success from placeholder commands.

This phase establishes the verification foundation for later Firebase, provider, browser, and live-demo phases. It does not claim that external providers or a real browser voice session work; those require later integration and browser phases.

## Numbers

| Value | Number | Source |
|---|---:|---|
| Minimum Python version | 3.12 | Existing README prerequisite |
| Maximum resume upload | 5 MB | Existing SPEC.md product requirement |
| Default interview retention | 14 days | Existing SPEC.md product requirement |
| Backend aggregate coverage floor | 80% | `scripts/test_backend.sh --fail-under=80` |
| Frontend line/function/statement floor | 80% | `frontend/package.json` c8 `--lines 80 --functions 80 --statements 80` |
| Frontend branch coverage floor | 70% | `frontend/package.json` c8 `--branches 70` |

## Out of scope

- Firebase, Firestore, STT, TTS, LLM, or WebRTC provider integrations
- Real browser automation and microphone testing
- Production deployment or hosted observability
- Product UI redesign
- Changing domain behavior unrelated to testability or validation

## Acceptance

- [ ] Marker contract written before implementation
- [ ] All existing backend tests execute real public behavior and contain no source-inspection tests
- [ ] A clean documented environment has explicit backend and frontend test commands
- [ ] Required lint, type-check, test, build, and coverage tools cannot silently skip
- [ ] CI executes backend checks, frontend checks, offline evidence, and coverage on pull requests
- [ ] CI uploads useful reports and fails on any required check failure
- [ ] Offline tests remain credential-free and network-independent
- [ ] The mock-turn evidence prints every required marker with no forbidden failure pattern
- [ ] Coverage thresholds are measured, documented, and enforced
- [ ] Any engine surprise is recorded in AGENTS.md invariants
