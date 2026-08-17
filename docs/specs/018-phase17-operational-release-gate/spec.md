# Spec 018 - Phase 17 operational release gate

## What this phase delivers

The repository gains a repeatable release-candidate gate for the first live launch. The gate inspects the documented production composition, validates the frontend build and backend quality commands, checks that production configuration fails closed when incomplete, and writes redacted JSON and Markdown evidence. A failed or unexercised prerequisite remains a blocker. The gate must never report launch readiness from deterministic tests alone.

## User and operator experience

An operator runs `scripts/test_phase17.sh`. The command reports each Phase 17 gate as `passed`, `blocked`, or `skipped`, writes evidence under `.agent_tmp/phase17-evidence`, and exits nonzero unless all required gates pass. Evidence contains no credentials, tokens, private keys, personal data, raw audio, or provider payloads.

## Scope

- Validate a clean Docker Compose release-candidate definition.
- Validate frontend lint, tests, and production build.
- Validate backend lint, type checking, tests, and mock-turn behavior.
- Validate production configuration fails closed when required live settings are absent.
- Record explicit open browser, security, durable-service, media, observability, rollback, and incident-runbook blockers.

## Out of scope

- Claiming Firebase, WhisperX, Kokoro, OpenRouter, browser identity, microphone, WebRTC, TURN, HTTPS, or external deployment operation without exercising them.
- Publishing, pushing, deploying, or creating a pull request.
- Replacing the existing Phase 16 live-provider rehearsal.

## Acceptance

- [x] Spec, plan, and marker contract exist before implementation.
- [ ] The gate emits every marker in the contract and redacted evidence.
- [ ] The gate fails when the release candidate is incomplete or a required command fails.
- [ ] The gate distinguishes deterministic checks from live-provider and browser evidence.
- [ ] Focused tests, lint/typecheck, backend, frontend, and mock-turn checks pass where configured.
- [ ] PLAN.md and README.md state the resulting launch status accurately.
