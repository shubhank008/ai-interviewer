"""Optional provider adapters with normalized, dependency-injected boundaries."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from ..contracts import CancellationToken, CapabilityDescriptor, ErrorCode, HealthStatus, ProviderError
from ..models import TranscriptSegment


class WhisperBackend(Protocol):
    """Minimal synchronous boundary for a Faster-Whisper compatible backend."""

    def transcribe(self, audio: bytes) -> str: ...


class SpeechBackend(Protocol):
    """Minimal boundary for Piper or Kokoro-compatible speech synthesis."""

    def synthesize(self, text: str) -> bytes: ...


class OpenRouterTransport(Protocol):
    """Transport boundary for an OpenAI-compatible hosted chat endpoint."""

    async def complete(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]: ...


class FasterWhisperSTT:
    """Adapt an injected Faster-Whisper model without importing it at module load."""

    def __init__(self, backend: WhisperBackend | None = None, model_name: str = "base.en") -> None:
        self.backend = backend
        self.model_name = model_name

    async def transcribe(self, audio: bytes, turn_id: UUID, token: CancellationToken) -> TranscriptSegment:
        """Transcribe bounded audio through the optional local backend."""
        token.raise_if_cancelled()
        if not audio:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "audio payload is empty")
        if self.backend is None:
            raise ProviderError(ErrorCode.UNAVAILABLE, "faster-whisper dependency is not configured", True)
        try:
            text = self.backend.transcribe(audio)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.INTERNAL, "local STT backend failed", True) from exc
        if not text.strip():
            raise ProviderError(ErrorCode.INTERNAL, "local STT returned empty text")
        return TranscriptSegment(turn_id, "candidate", text.strip())

    def capabilities(self) -> CapabilityDescriptor:
        """Describe local batch transcription behavior."""
        return CapabilityDescriptor("faster-whisper", False, True)

    async def health(self) -> HealthStatus:
        """Report dependency readiness without downloading model weights."""
        return HealthStatus(self.backend is not None, "configured" if self.backend else "dependency not configured")


class PiperKokoroTTS:
    """Adapt an injected Piper or Kokoro-compatible CPU speech backend."""

    def __init__(self, backend: SpeechBackend | None = None, voice: str = "default") -> None:
        self.backend = backend
        self.voice = voice

    async def synthesize(self, text: str, token: CancellationToken) -> bytes:
        """Synthesize non-empty text without selecting a vendor in domain code."""
        token.raise_if_cancelled()
        if not text.strip():
            raise ProviderError(ErrorCode.INVALID_REQUEST, "text is empty")
        if self.backend is None:
            raise ProviderError(ErrorCode.UNAVAILABLE, "local TTS dependency is not configured", True)
        try:
            audio = self.backend.synthesize(text)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(ErrorCode.INTERNAL, "local TTS backend failed", True) from exc
        if not audio:
            raise ProviderError(ErrorCode.INTERNAL, "local TTS returned empty audio")
        return audio

    def capabilities(self) -> CapabilityDescriptor:
        """Describe local non-streaming speech synthesis."""
        return CapabilityDescriptor("piper-kokoro", False, True)

    async def health(self) -> HealthStatus:
        """Report whether an injected speech dependency is ready."""
        return HealthStatus(self.backend is not None, "configured" if self.backend else "dependency not configured")


class OpenRouterLLM:
    """Adapt an OpenAI-compatible hosted completion transport with optional credentials."""

    def __init__(self, transport: OpenRouterTransport | None = None, api_key: str | None = None, model: str = "default") -> None:
        self.transport = transport
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, token: CancellationToken) -> str:
        """Generate text while keeping authentication and wire formats adapter-local."""
        token.raise_if_cancelled()
        if not prompt.strip():
            raise ProviderError(ErrorCode.INVALID_REQUEST, "prompt is empty")
        if self.transport is None or not self.api_key:
            raise ProviderError(ErrorCode.UNAVAILABLE, "hosted LLM transport or credential is not configured", True)
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        try:
            result = await self.transport.complete(payload, self.api_key)
            text = str(result["choices"][0]["message"]["content"])
        except ProviderError:
            raise
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(ErrorCode.INTERNAL, "hosted LLM response was malformed") from exc
        except Exception as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "hosted LLM request failed", True) from exc
        if not text.strip():
            raise ProviderError(ErrorCode.INTERNAL, "hosted LLM returned empty text")
        return text.strip()

    def capabilities(self) -> CapabilityDescriptor:
        """Describe the hosted completion behavior."""
        return CapabilityDescriptor("openrouter", False, True)

    async def health(self) -> HealthStatus:
        """Report local configuration only, without making a network request."""
        ready = self.transport is not None and bool(self.api_key)
        return HealthStatus(ready, "configured" if ready else "transport or credential not configured")
