# Plan 018 - Phase 17 operational release gate

## Global Constraints

- Do not claim live launch readiness from deterministic tests or configuration presence.
- Keep credentials, provider payloads, personal data, audio bytes, and private keys out of evidence.
- Production must fail closed and must not compose in-memory providers.
- Existing capability interfaces and Phase 16 rehearsal remain unchanged.
- Use repository-provided commands and avoid modifying package registries or system configuration.
- Do not publish or deploy from this implementation branch.

## Work order

1. Define marker and evidence contracts.
2. Implement a shell gate with isolated checks and redacted JSON/Markdown output.
3. Add behavior tests for pass, blocker, and redaction behavior.
4. Run the complete deterministic verification suite and inspect the evidence.
5. Update roadmap and launch-readiness documentation.

## Files expected to change

- `scripts/test_phase17.sh`
- `tests/test_phase17_release_gate.py`
- `docs/specs/018-phase17-operational-release-gate/*`
- `PLAN.md`
- `README.md`
