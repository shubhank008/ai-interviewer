#!/usr/bin/env sh
set -eu

export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
output="$(mktemp)"
trap 'rm -f "$output"' EXIT
python -m unittest tests.test_configuration -v 2>&1 | tee "$output"
for marker in \
  '[PHASE11] config-local-ok' \
  '[PHASE11] config-production-fail-safe' \
  '[PHASE11] provider-health-capabilities-ok' \
  '[PHASE11] provider-fallback-e2e-ok' \
  '[PHASE11] mock-runtime-e2e-ok' \
  '[PHASE11] diagnostics-redacted'; do
  grep -F "$marker" "$output" >/dev/null
done
if grep -E 'Traceback|Script Error|secret leaked|raw provider key|Firebase private key|Bearer dev-token|NotImplementedError|TODO: production|placeholder|skipped required check' "$output" >/dev/null; then
  printf '%s\n' 'forbidden Phase 11 failure pattern found' >&2
  exit 1
fi
printf '%s\n' '[PHASE11] markers-ok'
