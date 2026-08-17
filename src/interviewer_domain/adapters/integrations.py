"""Opt-in concrete provider transports and integration evidence.

The module is intentionally lazy: importing the domain package never imports an
SDK, downloads a model, opens a socket, or reads a credential-bearing file.
"""

from __future__ import annotations

import asyncio
import html
import json
import os
import random
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, List, Mapping

from ..contracts import ErrorCode, ProviderError


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



class LocalWhisperBackend:
    """Run an operator-selected OpenAI Whisper or WhisperX model locally."""

    def __init__(self, provider: str, model: str, device: str, language: str | None = None, model_path: str | None = None) -> None:
        self.provider = provider
        self.model_name = model
        self.device = device
        self.language = language
        self.model_path = model_path
        if provider == "whisperx":
            try:
                import whisperx  # type: ignore[import-not-found,import-untyped]
            except ImportError as exc:
                raise IntegrationSkipped("whisperx package is not installed") from exc
            self.model = whisperx.load_model(
                model,
                device,
                compute_type="float32" if device != "cpu" else "int8",
                language=language,
                vad_method="silero",
            )
        elif provider == "openai-whisper":
            try:
                import whisper  # type: ignore[import-not-found]
            except ImportError as exc:
                raise IntegrationSkipped("openai-whisper package is not installed") from exc
            self.model = whisper.load_model(model, device=device)
        else:
            raise IntegrationSkipped("unsupported local Whisper provider")

    def transcribe(self, audio: bytes) -> str:
        """Decode common audio bytes and return normalized transcript text."""
        if not audio:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "audio payload is empty")
        try:
            import io
            import soundfile as sf  # type: ignore[import-not-found,import-untyped]
            import numpy as np  # type: ignore[import-not-found]
            samples, sample_rate = sf.read(io.BytesIO(audio), dtype="float32")
            if getattr(samples, "ndim", 1) > 1:
                samples = samples.mean(axis=1)
            if sample_rate != 16000:
                target_length = round(len(samples) * 16000 / sample_rate)
                source_positions = np.linspace(0, 1, len(samples), endpoint=False)
                target_positions = np.linspace(0, 1, target_length, endpoint=False)
                samples = np.interp(target_positions, source_positions, samples).astype("float32")
            samples = np.asarray(samples, dtype="float32")
            if self.provider == "whisperx":
                result = self.model.transcribe(samples, language=self.language)
                text = str(result.get("text", "")).strip()
                if text:
                    return text
                segments, _ = self.model.model.transcribe(
                    samples,
                    language=self.language,
                    vad_filter=False,
                    without_timestamps=True,
                )
                return " ".join(str(segment.text).strip() for segment in segments).strip()
            result = self.model.transcribe(samples, language=self.language, fp16=self.device != "cpu")
            return str(result.get("text", "")).strip()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.INTERNAL, "local speech recognition failed", True) from exc

    def metadata(self) -> ProviderMetadata:
        """Return safe provider metadata without exposing model paths."""
        return ProviderMetadata(self.provider, self.model_name, "installed", "local", self.device)


class KokoroPythonBackend:
    """Run the official Kokoro Python pipeline with an injected model choice."""

    _ENGLISH_VOICES = (
        "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
        "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
        "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
        "am_michael", "am_onyx", "am_puck",
    )

    def __init__(self, language: str = "en", voice: str = "af_heart") -> None:
        try:
            from kokoro import KPipeline  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise IntegrationSkipped("kokoro package is not installed") from exc
        self.language = language
        self.voice = voice
        self.pipeline = KPipeline(lang_code=language[0])

    def _voice_for_call(self) -> str:
        """Select a supported English voice for each default synthesis call."""
        if self.voice not in {"", "default"}:
            return self.voice
        if self.language.startswith("en"):
            return random.choice(self._ENGLISH_VOICES)
        raise ProviderError(ErrorCode.INVALID_REQUEST, "default Kokoro voice is only configured for English")

    def synthesize(self, text: str) -> bytes:
        """Synthesize text into a normalized WAV byte payload."""
        if not text.strip():
            raise ProviderError(ErrorCode.INVALID_REQUEST, "text is empty")
        try:
            import io
            import soundfile as sf  # type: ignore[import-not-found,import-untyped]
            chunks = [audio for _, _, audio in self.pipeline(text, voice=self._voice_for_call())]
            if not chunks:
                raise ProviderError(ErrorCode.INTERNAL, "Kokoro returned empty audio")
            output = io.BytesIO()
            sf.write(output, chunks[0] if len(chunks) == 1 else _concat_audio(chunks), 24000, format="WAV")
            return output.getvalue()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.INTERNAL, "Kokoro synthesis failed", True) from exc

    def metadata(self) -> ProviderMetadata:
        """Return safe Kokoro metadata."""
        return ProviderMetadata("kokoro", self.voice, "installed", "local", "cpu")


def _concat_audio(chunks: list[Any]) -> Any:
    """Concatenate tensor or array chunks without importing either eagerly."""
    try:
        import numpy as np  # type: ignore[import-not-found]
        return np.concatenate([chunk.detach().cpu().numpy() if hasattr(chunk, "detach") else chunk for chunk in chunks])
    except Exception as exc:
        raise ProviderError(ErrorCode.INTERNAL, "Kokoro audio normalization failed") from exc


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


class SyncOpenRouterHTTPTransport:
    """Synchronous OpenRouter transport using the OpenAI-compatible HTTP contract."""

    def __init__(self, base_url: str = "https://openrouter.ai/api/v1", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        """Send one bounded synchronous request and normalize network or payload failures."""
        if not api_key:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "provider credential is missing")
        try:
            import httpx

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                value = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderError(ErrorCode.TIMEOUT, "hosted LLM request timed out", True) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "hosted LLM request failed", True) from exc
        if not isinstance(value, dict):
            raise ProviderError(ErrorCode.INTERNAL, "hosted LLM response was malformed")
        return value


class FasterWhisperLocalBackend:
    """Load an operator-selected Faster-Whisper model by name."""

    def __init__(self, model: str, device: str = "cpu", compute_type: str = "int8") -> None:
        self.model_name = Path(model).name if Path(model).is_dir() else model
        self.device = device
        self.compute_type = compute_type
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise IntegrationSkipped("faster-whisper package is not installed") from exc
        model_path = Path(model).expanduser()
        if model_path.is_absolute() and not model_path.is_dir():
            raise IntegrationSkipped("local Faster-Whisper model path is unavailable")
        sdk_module = getattr(WhisperModel, "__module__", "")
        if (
            model_path.is_dir()
            and not (model_path / "model.bin").is_file()
            and isinstance(sdk_module, str)
            and sdk_module.startswith("faster_whisper")
        ):
            raise IntegrationSkipped("local Faster-Whisper model path is incomplete")
        try:
            if model_path.is_dir():
                try:
                    self.model = WhisperModel(str(model_path), device=device, compute_type=compute_type, local_files_only=True)
                except TypeError:
                    self.model = WhisperModel(str(model_path), device=device, compute_type=compute_type)
            else:
                self.model = WhisperModel(model, device=device, compute_type=compute_type)
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "Faster-Whisper model could not be loaded") from exc

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
        """Return safe model-name, version, and device metadata."""
        return ProviderMetadata("faster-whisper", self.model_name, "installed", "local", self.device, limitation="batch audio path")


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
            import firebase_admin  # type: ignore[import-not-found,import-untyped]
            from firebase_admin import auth, credentials  # type: ignore[import-not-found]
        except ImportError as exc:
            raise IntegrationSkipped("firebase-admin package is not installed") from exc
        try:
            if not firebase_admin._apps:
                if not credential_path and not project_id:
                    raise IntegrationSkipped("Firebase ADC requires FIREBASE_PROJECT_ID")
                options = {"projectId": project_id} if project_id else None
                credential = credentials.Certificate(credential_path) if credential_path else credentials.ApplicationDefault()
                firebase_admin.initialize_app(credential, options)
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

    def __init__(
        self, project_id: str, database: str = "(default)", credential_path: str | None = None
    ) -> None:
        try:
            from google.cloud import firestore  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise IntegrationSkipped("google-cloud-firestore package is not installed") from exc
        try:
            credentials = None
            if credential_path:
                from google.oauth2 import service_account  # type: ignore[import-not-found,import-untyped]

                credentials = service_account.Credentials.from_service_account_file(credential_path)
            self.client = firestore.Client(
                project=project_id, database=database, credentials=credentials
            )
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "Firestore setup failed") from exc

    def _collection(self, name: str):
        return self.client.collection(name)

    def set(self, collection: str, document_id: str, value: dict[str, Any]) -> None:
        self._collection(collection).document(document_id).set(value)

    def get(self, collection: str, document_id: str) -> dict[str, Any] | None:
        value = self._collection(collection).document(document_id).get()
        return value.to_dict() if value.exists else None

    def delete_document(self, collection: str, document_id: str) -> None:
        """Delete one document while leaving unrelated owner records untouched."""
        self._collection(collection).document(document_id).delete()

    def list(self, collection: str, field: str, value: str) -> list[dict[str, Any]]:
        return [doc.to_dict() for doc in self._collection(collection).where(field, "==", value).stream()]

    def list_range(self, collection: str, field: str, op: str, value: str) -> List[dict[str, Any]]:
        return [doc.to_dict() for doc in self._collection(collection).where(field, op, value).stream()]

    def list_all(self, collection: str) -> List[dict[str, Any]]:
        """Return all documents in a collection for retention administration."""
        return [doc.to_dict() for doc in self._collection(collection).stream()]

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
            import boto3  # type: ignore[import-not-found,import-untyped]
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


class FirebaseStorageBackend:
    """Adapt Firebase Storage through the official Admin SDK bucket API."""

    def __init__(
        self,
        bucket_name: str | None = None,
        credential_path: str | None = None,
        project_id: str | None = None,
    ) -> None:
        try:
            import firebase_admin  # type: ignore[import-not-found,import-untyped]
            from firebase_admin import credentials, storage  # type: ignore[import-not-found]
        except ImportError as exc:
            raise IntegrationSkipped("firebase-admin package is not installed") from exc
        try:
            if not credential_path and not project_id:
                raise IntegrationSkipped("Firebase Storage requires credentials or project ID")
            options = {"projectId": project_id} if project_id else None
            credential = (
                credentials.Certificate(credential_path)
                if credential_path
                else credentials.ApplicationDefault()
            )
            app_name = "phase16-storage"
            try:
                app = firebase_admin.get_app(app_name)
            except ValueError:
                app = firebase_admin.initialize_app(credential, options, name=app_name)
            normalized_bucket = bucket_name.removeprefix("gs://") if bucket_name else None
            self.bucket = storage.bucket(normalized_bucket, app=app)
        except IntegrationSkipped:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "Firebase Storage setup failed") from exc

    def put_object(self, key: str, content: bytes, content_type: str) -> None:
        """Upload one opaque object with an explicit content type."""
        try:
            blob = self.bucket.blob(key)
            blob.upload_from_string(content, content_type=content_type)
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "Firebase Storage upload failed", True) from exc

    def get_object(self, key: str) -> bytes:
        """Download one object or report a normalized not-found error."""
        try:
            return bytes(self.bucket.blob(key).download_as_bytes())
        except Exception as exc:
            raise KeyError(key) from exc

    def delete_prefix(self, prefix: str) -> None:
        """Delete every object under an owner-scoped prefix."""
        try:
            for blob in self.bucket.list_blobs(prefix=prefix):
                blob.delete()
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "Firebase Storage deletion failed", True) from exc


def configured_profiles(environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """Return explicitly selected profiles, never adding a default profile."""
    values = environ or os.environ
    return tuple(item.strip() for item in values.get("PHASE15_PROFILES", "").split(",") if item.strip())


def skip_reason(profile: str, environ: Mapping[str, str] | None = None) -> str:
    """Return a precise safe reason without revealing credential values."""
    values = os.environ if environ is None else environ
    requirements = {
        "openrouter": ("LLM_API_KEY", "LLM_MODEL"),
        "faster-whisper": ("STT_MODEL",),
        "piper": ("TTS_MODEL", "TTS_COMMAND"),
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
    def escape_md(s: str) -> str:
        return s.replace("|", "\\|")

    rows = "\n".join(f"| {escape_md(item.capability)} | {escape_md(item.status)} | {escape_md(item.reason)} |" for item in evidence)
    markdown_path.write_text("# Phase 15 provider integration evidence\n\n| Capability | Status | Safe reason |\n|---|---|---|\n" + rows + "\n", encoding="utf-8")
    html_path.write_text("<!doctype html><meta charset='utf-8'><title>Phase 15 evidence</title><h1>Phase 15 provider integration evidence</h1><table><tr><th>Capability</th><th>Status</th><th>Reason</th></tr>" + "".join(f"<tr><td>{html.escape(item.capability)}</td><td>{html.escape(item.status)}</td><td>{html.escape(item.reason)}</td></tr>" for item in evidence) + "</table>\n", encoding="utf-8")
    return json_path, markdown_path, html_path
