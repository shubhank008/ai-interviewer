"""Run the Phase 17 deterministic release-candidate gate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class GateResult:
    """Redacted result for one release gate."""

    name: str
    status: str
    detail: str


LIVE_BLOCKERS = (
    "Browser Firebase identity and cross-user owner isolation are not exercised.",
    "Browser microphone, WebSocket media routing, WebRTC, and TURN are not exercised.",
    "HTTPS, secure origins, production CORS, secret injection, and rate-limit deployment are not verified.",
    "Durable retention scheduling, monitoring, alerting, backup/restore, rollback, and incident procedures are not verified.",
    "A clean deployed release candidate has not been run against the selected live providers.",
)


def run(
    command: Sequence[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout_seconds: int = 180,
) -> tuple[bool, str]:
    """Run a repository command and return only a bounded diagnostic."""
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout_seconds}s"
    except OSError as error:
        return False, f"could not start command: {error.__class__.__name__}"
    detail = " ".join(completed.stdout.split())[-300:]
    return completed.returncode == 0, detail or "completed"


def production_fails_closed_missing_required(root: Path) -> tuple[bool, str]:
    """Verify incomplete production settings are rejected before composition."""
    env = os.environ.copy()
    env.update({"PYTHONPATH": str(root / "src"), "APP_PROFILE": "production"})
    for key in (
        "FIREBASE_PROJECT_ID",
        "FIRESTORE_DATABASE",
        "LLM_API_KEY",
        "STT_API_KEY",
        "TTS_API_KEY",
    ):
        env.pop(key, None)
    code = (
        "from interviewer_domain.configuration import RuntimeSettings, ConfigurationError\n"
        "try:\n"
        "    RuntimeSettings.from_env()\n"
        "except ConfigurationError:\n"
        "    pass\n"
        "else:\n"
        "    raise SystemExit(2)\n"
    )
    return run([sys.executable, "-c", code], root, env)


def production_fails_closed_local_storage(root: Path) -> tuple[bool, str]:
    """Verify production rejects STORAGE_BACKEND=local."""
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(root / "src"),
        "APP_PROFILE": "production",
        "FIREBASE_PROJECT_ID": "test-project",
        "FIRESTORE_DATABASE": "(default)",
        "STT_PROVIDER": "whisperx",
        "TTS_PROVIDER": "kokoro",
        "LLM_PROVIDER": "openrouter",
        "LLM_API_KEY": "test-key",
    })
    for key in ("STORAGE_BACKEND", "CORS_ORIGINS", "METRICS_ENABLED", "STORAGE_BUCKET"):
        env.pop(key, None)
    code = (
        "from interviewer_domain.configuration import RuntimeSettings, ConfigurationError\n"
        "try:\n"
        "    RuntimeSettings.from_env()\n"
        "except ConfigurationError as exc:\n"
        "    if 'STORAGE_BACKEND' not in str(exc):\n"
        "        raise SystemExit(3)\n"
        "else:\n"
        "    raise SystemExit(2)\n"
    )
    return run([sys.executable, "-c", code], root, env)


def production_fails_closed_localhost_cors(root: Path) -> tuple[bool, str]:
    """Verify production rejects localhost CORS origins."""
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(root / "src"),
        "APP_PROFILE": "production",
        "FIREBASE_PROJECT_ID": "test-project",
        "FIRESTORE_DATABASE": "(default)",
        "STT_PROVIDER": "whisperx",
        "TTS_PROVIDER": "kokoro",
        "LLM_PROVIDER": "openrouter",
        "LLM_API_KEY": "test-key",
        "STORAGE_BACKEND": "gcs",
        "STORAGE_BUCKET": "test-bucket",
        "CORS_ORIGINS": "http://localhost:5173",
    })
    env.pop("METRICS_ENABLED", None)
    code = (
        "from interviewer_domain.configuration import RuntimeSettings, ConfigurationError\n"
        "try:\n"
        "    RuntimeSettings.from_env()\n"
        "except ConfigurationError as exc:\n"
        "    if 'CORS_ORIGINS' not in str(exc):\n"
        "        raise SystemExit(3)\n"
        "else:\n"
        "    raise SystemExit(2)\n"
    )
    return run([sys.executable, "-c", code], root, env)


def production_fails_closed_metrics_disabled(root: Path) -> tuple[bool, str]:
    """Verify production rejects disabled metrics."""
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(root / "src"),
        "APP_PROFILE": "production",
        "FIREBASE_PROJECT_ID": "test-project",
        "FIRESTORE_DATABASE": "(default)",
        "STT_PROVIDER": "whisperx",
        "TTS_PROVIDER": "kokoro",
        "LLM_PROVIDER": "openrouter",
        "LLM_API_KEY": "test-key",
        "STORAGE_BACKEND": "gcs",
        "STORAGE_BUCKET": "test-bucket",
        "CORS_ORIGINS": "https://app.example.com",
    })
    env.pop("METRICS_ENABLED", None)
    code = (
        "from interviewer_domain.configuration import RuntimeSettings, ConfigurationError\n"
        "try:\n"
        "    RuntimeSettings.from_env()\n"
        "except ConfigurationError as exc:\n"
        "    if 'metrics' not in str(exc).lower():\n"
        "        raise SystemExit(3)\n"
        "else:\n"
        "    raise SystemExit(2)\n"
    )
    return run([sys.executable, "-c", code], root, env)


def write_evidence(output_dir: Path, results: list[GateResult], blockers: tuple[str, ...]) -> None:
    """Write redacted machine-readable and operator-readable evidence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {"phase": 17, "results": [asdict(result) for result in results], "launch_blockers": list(blockers)}
    (output_dir / "phase17-release-gate.json").write_text(json.dumps(payload, indent=2) + "\n")
    lines = ["# Phase 17 release gate", "", "## Deterministic results", ""]
    lines.extend(f"- `{result.status}`: {result.name} - {result.detail}" for result in results)
    lines.extend(["", "## Live launch blockers", ""])
    lines.extend(f"- {blocker}" for blocker in blockers)
    (output_dir / "phase17-release-gate.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    """Run all checks, print contract markers, and fail while blockers remain."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=".agent_tmp/phase17-evidence")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    results: list[GateResult] = []

    checks = (
        ("docker-compose-definition-ok", ["docker", "compose", "config", "--quiet"], "docker compose definition"),
        ("backend-quality-ok", ["sh", "scripts/lint_and_typecheck.sh"], "backend lint and typecheck"),
        ("backend-tests-ok", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], "backend tests"),
        ("mock-interview-e2e-ok", [sys.executable, "scripts/run_mock_turn.py"], "mock interview"),
        ("frontend-quality-ok", ["npm", "run", "lint", "--prefix", "frontend"], "frontend lint"),
        ("frontend-tests-ok", ["npm", "test", "--prefix", "frontend"], "frontend tests"),
        ("frontend-build-ok", ["npm", "run", "build", "--prefix", "frontend"], "frontend build"),
    )
    for marker, command, label in checks:
        print(f"[RELEASE17] check-start name={label}", flush=True)
        ok, detail = run(command, root, {**os.environ, "PYTHONPATH": str(root / "src")})
        results.append(GateResult(label, "passed" if ok else "blocked", detail))
        print(f"[RELEASE17] check-result name={label} status={'passed' if ok else 'blocked'}", flush=True)
        if ok:
            print(f"[RELEASE17] {marker}", flush=True)

    production_checks = [
        ("production fails closed (missing required)", production_fails_closed_missing_required),
        ("production fails closed (local storage)", production_fails_closed_local_storage),
        ("production fails closed (localhost CORS)", production_fails_closed_localhost_cors),
        ("production fails closed (metrics disabled)", production_fails_closed_metrics_disabled),
    ]
    for label, check_fn in production_checks:
        print(f"[RELEASE17] check-start name={label}", flush=True)
        ok, detail = check_fn(root)
        results.append(GateResult(label, "passed" if ok else "blocked", detail))
        if ok:
            print(f"[RELEASE17] production-fails-closed-ok name={label}", flush=True)

    blockers = LIVE_BLOCKERS
    results.append(GateResult("live launch blockers", "blocked", f"{len(blockers)} open release gates"))
    output_dir = root / args.output_dir
    write_evidence(output_dir, results, blockers)
    print(f"[RELEASE17] launch-blockers-recorded count={len(blockers)}")
    print(f"[RELEASE17] evidence-written path={output_dir.relative_to(root)}")
    return 1 if any(result.status == "blocked" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
