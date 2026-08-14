#!/usr/bin/env sh
set -eu

export PATH="$(pwd)/.venv/bin:$PATH"
export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
export PHASE16_RESUME_FIXTURE="${PHASE16_RESUME_FIXTURE:-tests/demo_resume.pdf}"
export PHASE16_JOB_FIXTURE="${PHASE16_JOB_FIXTURE:-tests/demo_jobdescription.txt}"
export PHASE16_AUDIO_TRANSPORT="${PHASE16_AUDIO_TRANSPORT:-agent-buffer}"
for fixture in "$PHASE16_RESUME_FIXTURE" "$PHASE16_JOB_FIXTURE"; do
  if [ ! -f "$fixture" ]; then
    echo "[BETA16] missing-fixture path=$fixture" >&2
    exit 1
  fi
done
output_dir="${PHASE16_EVIDENCE_DIR:-.agent_tmp/phase16-evidence}"
export PHASE16_EVIDENCE_DIR="$output_dir"
mkdir -p "$output_dir"
"$PWD/.venv/bin/python" -m unittest tests.test_phase16_beta tests.test_phase16_rehearsal -v >"$output_dir/test.log"
"$PWD/.venv/bin/python" - <<'PY' >"$output_dir/markers.log"
import os
from interviewer_domain.phase16_rehearsal import Phase16Rehearsal, load_dotenv, write_rehearsal_evidence

environ = load_dotenv(".env", os.environ)
results = Phase16Rehearsal(environ=environ).run()
for result in results:
    print(f"[BETA16] {result.operation.marker} status={result.status} reason={result.reason}")
path = write_rehearsal_evidence(os.environ.get("PHASE16_EVIDENCE_DIR", ".agent_tmp/phase16-evidence"), results)
print(f"[BETA16] evidence-written format={path.suffix[1:]}")
PY
if grep -E 'Traceback|Script Error|api_key|Authorization|Bearer |private key|Firebase private key|resume text|transcript text|audio bytes|raw provider payload' "$output_dir/test.log" "$output_dir/markers.log" "$output_dir"/*.json; then
  exit 1
fi
