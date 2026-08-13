#!/usr/bin/env sh
set -eu

export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
output_dir="${PHASE16_EVIDENCE_DIR:-.agent_tmp/phase16-evidence}"
export PHASE16_EVIDENCE_DIR="$output_dir"
mkdir -p "$output_dir"
python -m unittest tests.test_phase16_beta -v >"$output_dir/test.log"
python - <<'PY' >"$output_dir/markers.log"
import os
from interviewer_domain.configuration import ConfigurationError, RuntimeSettings, validate_beta_composition
from interviewer_domain.provider_integration import IntegrationEvidence, ProviderMetadata, redact_evidence, write_evidence

settings = RuntimeSettings.from_env(os.environ)
try:
    validate_beta_composition(settings)
except ConfigurationError:
    status, reason = "skipped", "required live beta configuration absent"
else:
    status, reason = "failed", "configured live beta execution requires the beta rehearsal runner"
print(f"[BETA16] composition-production-{status}")
evidence = [IntegrationEvidence("composition", status, reason, ProviderMetadata("beta-set", "configured" if status == "failed" else "not configured", limitation="offline gate does not claim live readiness"))]
paths = write_evidence(os.environ.get("PHASE16_EVIDENCE_DIR", ".agent_tmp/phase16-evidence"), evidence)
print("[BETA16] beta-evidence-redacted-ok")
for path in paths:
    print(f"[BETA16] evidence-written format={path.suffix[1:]}")
PY
if grep -E 'Traceback|Script Error|api_key|Authorization|Bearer |private key|Firebase private key|resume text|transcript text|audio bytes|raw provider payload' "$output_dir/test.log" "$output_dir/markers.log"; then
  exit 1
fi
