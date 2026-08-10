"""Opt-in concrete provider transports and integration evidence.

The module is intentionally lazy: importing the domain package never imports an
SDK, downloads a model, opens a socket, or reads a credential-bearing file.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import ErrorCode, ProviderError


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    """Safe provider identity and measurement metadata."""

    provider: str
    model: str
    version: str = "unknown"
    region: str = "unknown"
    device: str = "unknown"
    timing_ms: float | None = None
    estimated_cost: float | None = None
    quality: float | None = None
    limitation: str | None = None


@dataclass(frozen=True, slots=True)
class IntegrationEvidence:
    """One redacted exercised, skipped, or failed integration result."""

    capability: str
    status: str
    reason: str
    metadata: ProviderMetadata
    error_code: str | None = None


class IntegrationSkipped(RuntimeError):
    """Raised when an explicitly requested profile lacks safe configuration."""


class OpenRouterHTTPTransport:
    """Real OpenRouter transport using the OpenAI-compatible HTTP contract."""

    def __init__(self, base_url: str = "https://openrouter.ai/api/v1", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        """Send one bounded request and normalize network or payload failures."""
        if not api_key:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "provider credential is missing")
        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                value = response.json()
        except asyncio.TimeoutError as exc:
            raise ProviderError(ErrorCode.TIMEOUT, "hosted LLM request timed out", True) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "hosted LLM request failed", True) from exc
        if not isinstance(value, dict):
            raise ProviderError(ErrorCode.INTERNAL, "hosted LLM response was malformed")
        return value


class FasterWhisperLocalBackend:
    """Load a user-supplied Faster-Whisper model without downloading weights."""

    def __init__(self, model_path: str, device: str = "cpu", compute_type: str = "int8") -> None:
        path = Path(model_path).expanduser()
        if not path.exists() or not path.is_dir():
            raise IntegrationSkipped("local Faster-Whisper model path is unavailable")
        self.model_path = path
        self.device = device
        self.compute_type = compute_type
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise IntegrationSkipped("faster-whisper package is not installed") from exc
        try:
            self.model = WhisperModel(str(path), device=device, compute_type=compute_type, local_files_only=True)
        except TypeError:
            self.model = WhisperModel(str(path), device=device, compute_type=compute_type)
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "local STT model could not be loaded") from exc

    def transcribe(self, audio: bytes) -> str:
        """Transcribe audio through the loaded local model."""
        if not audio:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "audio payload is empty")
        try:
            segments, _ = self.model.transcribe(audio)
            return " ".join(str(segment.text).strip() for segment in segments).strip()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.INTERNAL, "local STT inference failed", True) from exc

    def metadata(self) -> ProviderMetadata:
        """Return safe model path, version, and device metadata."""
        return ProviderMetadata("faster-whisper", self.model_path.name, "installed", "local", self.device, limitation="batch audio path")


class PiperCommandBackend:
    """Synthesize through an operator-installed Piper or Kokoro command."""

    def __init__(self, command: str, model_path: str, sample_rate: int = 22050) -> None:
        path = Path(model_path).expanduser()
        if not path.is_file():
            raise IntegrationSkipped("local TTS model path is unavailable")
        if not command:
            raise IntegrationSkipped("local TTS command is not configured")
        self.command, self.model_path, self.sample_rate = command, path, sample_rate

    def synthesize(self, text: str) -> bytes:
        """Run the configured speech command without logging text or audio."""
        if not text.strip():
            raise ProviderError(ErrorCode.INVALID_REQUEST, "text is empty")
        try:
            result = subprocess.run(
                [self.command, "--model", str(self.model_path), "--output-raw"],
                input=text.encode(), capture_output=True, timeout=30, check=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(ErrorCode.TIMEOUT, "local TTS request timed out", True) from exc
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "local TTS command failed", True) from exc
        if not result.stdout:
            raise ProviderError(ErrorCode.INTERNAL, "local TTS returned empty audio")
        return result.stdout

    def metadata(self) -> ProviderMetadata:
        """Return model and playback metadata without audio content."""
        return ProviderMetadata("piper-kokoro", self.model_path.name, "installed", "local", "cpu", limitation=f"pcm/{self.sample_rate}Hz")


class FirebaseAdminAuthBackend:
    """Verify Firebase ID tokens with the official Admin SDK when configured."""

    def __init__(self, credential_path: str | None = None, project_id: str | None = None) -> None:
        try:
            import firebase_admin  # type: ignore[import-not-found]
            from firebase_admin import auth, credentials  # type: ignore[import-not-found]
        except ImportError as exc:
            raise IntegrationSkipped("firebase-admin package is not installed") from exc
        try:
            if not firebase_admin._apps:
                if not credential_path:
                    raise IntegrationSkipped("FIREBASE_CREDENTIALS_PATH is not configured")
                firebase_admin.initialize_app(credentials.Certificate(credential_path), {"projectId": project_id} if project_id else None)
            self._auth = auth
        except IntegrationSkipped:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "Firebase authentication setup failed") from exc

    def verify(self, token: str) -> dict[str, Any]:
        """Verify a token and return only normalized claims to the domain."""
        if not token:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "authentication token is empty")
        try:
            return dict(self._auth.verify_id_token(token, check_revoked=True))
        except Exception as exc:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "invalid authentication token") from exc


class FirestoreGoogleBackend:
    """Adapt the official Firestore client to the repository document seam."""

    def __init__(self, project_id: str, database: str = "(default)") -> None:
        try:
            from google.cloud import firestore  # type: ignore[import-untyped]
        except ImportError as exc:
            raise IntegrationSkipped("google-cloud-firestore package is not installed") from exc
        try:
            self.client = firestore.Client(project=project_id, database=database)
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "Firestore setup failed") from exc

    def _collection(self, name: str):
        return self.client.collection(name)

    def set(self, collection: str, document_id: str, value: dict[str, Any]) -> None:
        self._collection(collection).document(document_id).set(value)

    def get(self, collection: str, document_id: str) -> dict[str, Any] | None:
        value = self._collection(collection).document(document_id).get()
        return value.to_dict() if value.exists else None

    def list(self, collection: str, field: str, value: str) -> list[dict[str, Any]]:
        return [doc.to_dict() for doc in self._collection(collection).where(field, "==", value).stream()]

    def delete_collection_value(self, collection: str, field: str, value: str) -> None:
        for doc in self._collection(collection).where(field, "==", value).stream():
            doc.reference.delete()

    def delete_collection(self, collection: str) -> None:
        for doc in self._collection(collection).stream():
            doc.reference.delete()


class Boto3ObjectBackend:
    """Adapt an S3-compatible bucket to the repository object seam."""

    def __init__(self, bucket: str, endpoint_url: str | None = None, region: str | None = None) -> None:
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:
            raise IntegrationSkipped("boto3 package is not installed") from exc
        self.bucket = bucket
        self.client = boto3.client("s3", endpoint_url=endpoint_url, region_name=region)

    def put_object(self, key: str, content: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType=content_type)

    def get_object(self, key: str) -> bytes:
        try:
            return bytes(self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read())
        except Exception as exc:
            raise KeyError(key) from exc

    def delete_prefix(self, prefix: str) -> None:
        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        keys = [{"Key": item["Key"]} for item in response.get("Contents", [])]
        if keys:
            self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys})


def configured_profiles(environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """Return explicitly selected profiles, never adding a default profile."""
    values = environ or os.environ
    return tuple(item.strip() for item in values.get("PHASE15_PROFILES", "").split(",") if item.strip())


def skip_reason(profile: str, environ: Mapping[str, str] | None = None) -> str:
    """Return a precise safe reason without revealing credential values."""
    values = environ or os.environ
    requirements = {
        "openrouter": ("OPENROUTER_API_KEY", "LLM_MODEL"),
        "faster-whisper": ("STT_MODEL_PATH",),
        "piper": ("TTS_MODEL_PATH", "TTS_COMMAND"),
        "firebase": ("FIREBASE_PROJECT_ID", "FIREBASE_CREDENTIALS_PATH"),
        "firestore": ("FIREBASE_PROJECT_ID",),
        "storage": ("STORAGE_BUCKET",),
        "webrtc": ("PHASE15_BROWSER_URL",),
    }
    missing = [key for key in requirements.get(profile, ()) if not values.get(key)]
    return "required configuration absent: " + ", ".join(missing) if missing else "profile is configured"


def redact_evidence(evidence: IntegrationEvidence) -> dict[str, Any]:
    """Serialize safe metadata only; never include provider payloads."""
    value = asdict(evidence)
    value["metadata"] = {key: item for key, item in asdict(evidence.metadata).items() if item is not None}
    return value


def write_evidence(path: str | Path, evidence: list[IntegrationEvidence]) -> tuple[Path, Path, Path]:
    """Write redacted JSON, Markdown, and HTML integration evidence."""
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    payload = [redact_evidence(item) for item in evidence]
    json_path, markdown_path, html_path = target / "phase15-report.json", target / "phase15-report.md", target / "phase15-report.html"
    json_path.write_text(json.dumps({"schema_version": 1, "integrations": payload}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = "\n".join(f"| {item.capability} | {item.status} | {item.reason} |" for item in evidence)
    markdown_path.write_text("# Phase 15 provider integration evidence\n\n| Capability | Status | Safe reason |\n|---|---|---|\n" + rows + "\n", encoding="utf-8")
    html_path.write_text("<!doctype html><meta charset='utf-8'><title>Phase 15 evidence</title><h1>Phase 15 provider integration evidence</h1><table><tr><th>Capability</th><th>Status</th><th>Reason</th></tr>" + "".join(f"<tr><td>{item.capability}</td><td>{item.status}</td><td>{item.reason}</td></tr>" for item in evidence) + "</table>\n", encoding="utf-8")
    return json_path, markdown_path, html_path
