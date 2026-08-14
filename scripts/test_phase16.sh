#!/usr/bin/env sh
set -eu

export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
output_dir="${PHASE16_EVIDENCE_DIR:-.agent_tmp/phase16-evidence}"
export PHASE16_EVIDENCE_DIR="$output_dir"
mkdir -p "$output_dir"
python -m unittest tests.test_phase16_beta tests.test_phase16_rehearsal -v >"$output_dir/test.log"
python - <<'PY' >"$output_dir/markers.log"
import os
from interviewer_domain.phase16_rehearsal import Phase16Rehearsal, write_rehearsal_evidence

results = Phase16Rehearsal(environ=os.environ).run()
for result in results:
    print(f"[BETA16] {result.operation.marker} status={result.status} reason={result.reason}")
path = write_rehearsal_evidence(os.environ.get("PHASE16_EVIDENCE_DIR", ".agent_tmp/phase16-evidence"), results)
print(f"[BETA16] evidence-written format={path.suffix[1:]}")
PY
if grep -E 'Traceback|Script Error|api_key|Authorization|Bearer |private key|Firebase private key|resume text|transcript text|audio bytes|raw provider payload' "$output_dir/test.log" "$output_dir/markers.log" "$output_dir"/*.json; then
  exit 1
fi
