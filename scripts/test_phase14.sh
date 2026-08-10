#!/usr/bin/env sh
set -eu

export PYTHONPATH="${PYTHONPATH:-}:src"
output_dir="${PHASE14_EVIDENCE_DIR:-.agent_tmp/phase14-evidence}"
mkdir -p "$output_dir"
python -m pytest -q tests/test_phase14_full_user_e2e.py >"$output_dir/test.log"
PHASE14_EVIDENCE_DIR="$output_dir" python - <<'PY'
import os

from interviewer_domain.e2e_acceptance import FORBIDDEN, run_local_acceptance_sync

report = run_local_acceptance_sync()
if not report.passed:
    raise SystemExit("Phase 14 acceptance failed: " + "; ".join(report.failures))
for marker in report.markers:
    print(marker)
for path in report.write(os.environ["PHASE14_EVIDENCE_DIR"]):
    print(f"[PHASE14] artifact={path}")
content = "\n".join(event.details.get("error", "") for event in report.events)
if any(pattern in content for pattern in FORBIDDEN):
    raise SystemExit("forbidden diagnostic pattern found")
PY
if grep -E 'Traceback|Script Error|secret leaked|Firebase private key|media tunneled over websocket|stale response spoken|NotImplementedError|placeholder|skipped required check|EXPECTED_STRING_SUBSTITUTION' "$output_dir/test.log"; then
  exit 1
fi
