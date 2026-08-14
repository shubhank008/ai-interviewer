"""Redacted Phase 16 live-beta rehearsal planning and evidence.

The runner deliberately does not treat deterministic providers as live evidence.
Concrete live executors can be registered by the deployment harness without
putting credentials, payloads, or personal data into the domain module.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping

from .adapters.integrations import IntegrationEvidence, ProviderMetadata, redact_evidence


@dataclass(frozen=True, slots=True)
class RehearsalOperation:
    """Describe one required live operation and its safe configuration keys."""

    marker: str
    capability: str
    provider: str
    required: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RehearsalResult:
    """Store a redacted operation result suitable for evidence output."""

    operation: RehearsalOperation
    status: str
    reason: str
    metadata: ProviderMetadata

    def evidence(self) -> IntegrationEvidence:
        """Convert the result to the shared provider evidence shape."""
        return IntegrationEvidence(
            self.operation.capability,
            self.status,
            self.reason,
            self.metadata,
        )


OPERATIONS: tuple[RehearsalOperation, ...] = (
    RehearsalOperation("composition-production-ok", "composition", "firebase/openrouter/whisperx/kokoro", ("APP_PROFILE", "FIREBASE_PROJECT_ID", "STT_PROVIDER", "TTS_PROVIDER", "LLM_PROVIDER", "LLM_API_KEY")),
    RehearsalOperation("firebase-auth-owner-isolation-ok", "firebase-auth", "firebase-auth", ("FIREBASE_PROJECT_ID", "FIREBASE_AUTH_DOMAIN")),
    RehearsalOperation("firestore-session-lifecycle-ok", "firestore", "firestore", ("FIREBASE_PROJECT_ID", "FIRESTORE_DATABASE")),
    RehearsalOperation("storage-firebase-lifecycle-ok", "storage-firebase", "firebase-storage", ("FIREBASE_PROJECT_ID", "STORAGE_BUCKET")),
    RehearsalOperation("storage-local-lifecycle-ok", "storage-local", "local/nfs", ("STORAGE_PATH",)),
    RehearsalOperation("resume-rag-context-ok", "resume-rag", "document-parser", ("PHASE16_RESUME_FIXTURE", "PHASE16_JOB_FIXTURE")),
    RehearsalOperation("agent-audio-transport-ok", "agent-audio", "timestamped-audio-buffers", ("PHASE16_AUDIO_TRANSPORT",)),
    RehearsalOperation("stt-partial-final-timestamps-ok", "stt", "whisperx-small", ("STT_PROVIDER", "STT_MODEL")),
    RehearsalOperation("llm-interviewer-stream-ok", "llm-interviewer", "openrouter", ("LLM_API_KEY", "LLM_MODEL")),
    RehearsalOperation("kokoro-audio-playback-ok", "tts", "kokoro", ("TTS_PROVIDER", "TTS_LANGUAGE")),
    RehearsalOperation("transcript-recording-persisted-ok", "transcript-recording", "selected-storage", ("FIREBASE_PROJECT_ID",)),
    RehearsalOperation("llm-evaluation-score-ok", "llm-evaluation", "openrouter", ("LLM_API_KEY", "LLM_MODEL")),
    RehearsalOperation("retention-deletion-ok", "retention-deletion", "selected-storage", ("FIREBASE_PROJECT_ID",)),
    RehearsalOperation("agent-recruiter-journey-ok", "agent-recruiter", "firebase/providers", ("FIREBASE_PROJECT_ID",)),
    RehearsalOperation("agent-technical-journey-ok", "agent-technical", "firebase/providers", ("FIREBASE_PROJECT_ID",)),
    RehearsalOperation("beta-evidence-redacted-ok", "beta-evidence", "redaction", ()),
)

Executor = Callable[[RehearsalOperation], RehearsalResult]


@dataclass(slots=True)
class Phase16Rehearsal:
    """Plan live operations and emit evidence without exposing sensitive data."""

    environ: Mapping[str, str] = field(default_factory=lambda: os.environ)
    executors: Mapping[str, Executor] = field(default_factory=dict)

    def run(self) -> tuple[RehearsalResult, ...]:
        """Run registered live seams and classify all other operations safely."""
        results: list[RehearsalResult] = []
        for operation in OPERATIONS:
            executor = self.executors.get(operation.marker)
            missing = tuple(key for key in operation.required if not self.environ.get(key))
            metadata = ProviderMetadata(operation.provider, "configured" if not missing else "not-configured", version="phase16", device="unknown")
            if operation.marker == "beta-evidence-redacted-ok" and executor is None:
                results.append(RehearsalResult(operation, "exercised", "redaction contract exercised", metadata))
            elif executor is not None:
                try:
                    result = executor(operation)
                except Exception:
                    result = RehearsalResult(operation, "failed", "live executor failed", metadata)
                results.append(result)
            elif missing:
                results.append(RehearsalResult(operation, "skipped", "required configuration absent", metadata))
            else:
                results.append(RehearsalResult(operation, "failed", "live executor not registered", metadata))
        return tuple(results)


def write_rehearsal_evidence(path: str | Path, results: tuple[RehearsalResult, ...]) -> Path:
    """Write only redacted JSON evidence and return its path."""
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "evidence_type": "phase16-live-beta-rehearsal",
        "operations": [
            {"marker": result.operation.marker, **redact_evidence(result.evidence())}
            for result in results
        ],
    }
    output = target / "phase16-rehearsal.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output
