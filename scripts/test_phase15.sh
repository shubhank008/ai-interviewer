#!/usr/bin/env sh
set -eu

export PYTHONPATH="${PYTHONPATH:-}:src"
output_dir="${PHASE15_EVIDENCE_DIR:-.agent_tmp/phase15-evidence}"
mkdir -p "$output_dir"
python -m unittest tests.test_provider_integration -v >"$output_dir/test.log"
PHASE15_EVIDENCE_DIR="$output_dir" python - <<'PY'
import os
from interviewer_domain.provider_integration import (
    IntegrationEvidence,
    ProviderMetadata,
    configured_profiles,
    skip_reason,
    write_evidence,
)

profiles = configured_profiles()
print("[PHASE15] profile-selected")
evidence = []
for profile in profiles:
    reason = skip_reason(profile)
    if reason != "profile is configured":
        evidence.append(IntegrationEvidence(profile, "skipped", reason, ProviderMetadata(profile, "not configured", limitation="not exercised")))
        print(f"[PHASE15] integration-skipped profile={profile} reason=configuration-absent")
    else:
        evidence.append(IntegrationEvidence(profile, "failed", "profile selected but execution is not enabled by this runner", ProviderMetadata(profile, "configured", limitation="manual adapter setup required"), "unavailable"))
        print(f"[PHASE15] integration-failed profile={profile} reason=execution-not-enabled")
if not profiles:
    for profile in ("openrouter", "faster-whisper", "piper", "firebase", "firestore", "storage", "webrtc"):
        evidence.append(IntegrationEvidence(profile, "skipped", skip_reason(profile), ProviderMetadata(profile, "not configured", limitation="profile not selected")))
        print(f"[PHASE15] integration-skipped profile={profile} reason=not-selected")
paths = write_evidence(os.environ["PHASE15_EVIDENCE_DIR"], evidence)
print("[PHASE15] evidence-redacted-ok")
for path in paths:
    print(f"[PHASE15] artifact={path}")
PY
if grep -E 'Traceback|Script Error|api_key|Authorization|Bearer |private key|Firebase private key|resume text|transcript text|audio bytes|raw provider payload' "$output_dir/test.log"; then
  exit 1
fi
