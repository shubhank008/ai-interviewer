# Plan 019 - Browser live-launch operations

## Global Constraints

- Do not claim browser, HTTPS, provider, or operational readiness without target-environment evidence.
- Owner isolation is excluded; only redacted authentication/resource markers are allowed.
- Keep credentials, tokens, audio bytes, personal data, and provider payloads out of logs and evidence.
- Keep frontend provider-neutral and backend provider interfaces unchanged.
- Production must use durable storage, non-local origins, non-in-memory providers, and fail-closed settings.
- Deterministic tests remain offline and use injected browser seams.

## Work order

1. Define this spec and marker contract.
2. Add redacted browser lifecycle markers and tests.
3. Add production frontend container and API/frontend Compose health checks.
4. Harden production origin and operational configuration validation.
5. Extend the release gate and evidence.
6. Run deterministic tests, Compose validation, and document live blockers.

## Files expected to change

- `frontend/src/auth.js`, `frontend/src/media.js`, `frontend/src/transport.js`
- `frontend/src/*test.js`
- `frontend/Dockerfile`, `frontend/nginx.conf`
- `Dockerfile`, `docker-compose.yml`
- `src/interviewer_domain/configuration.py`, `tests/test_configuration.py`
- `scripts/run_phase17_release_gate.py`, `tests/test_phase17_release_gate.py`
- `docs/specs/019-browser-live-launch-operations/*`, `PLAN.md`, `README.md`
