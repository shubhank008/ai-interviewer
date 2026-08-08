"""Capability protocols and normalized operational contracts."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from .models import LifecycleEvent, Recording, TranscriptSegment


class ErrorCode(StrEnum):
    """Stable error categories exposed by all providers."""

    INVALID_REQUEST = "invalid_request"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CONFLICT = "conflict"
    INTERNAL = "internal"


class ProviderError(Exception):
    """Normalized provider failure with safe, non-secret context."""

    def __init__(self, code: ErrorCode, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class CancellationToken:
    """Cooperative cancellation state shared by capability calls."""

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        """Mark the operation as cancelled."""
        self._cancelled = True

    def raise_if_cancelled(self) -> None:
        """Raise the normalized cancellation error when requested."""
        if self._cancelled:
            raise ProviderError(ErrorCode.CANCELLED, "operation cancelled")


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Provider health result."""

    healthy: bool
    detail: str = "ok"


@dataclass(frozen=True, slots=True)
class CapabilityDescriptor:
    """Provider capability discovery result."""

    name: str
    streaming: bool
    cancellation: bool


class LLMProvider(Protocol):
    """Generate normalized interviewer text."""

    async def generate(self, prompt: str, token: CancellationToken) -> str: ...

    def capabilities(self) -> CapabilityDescriptor: ...

    async def health(self) -> HealthStatus: ...


class STTProvider(Protocol):
    """Transcribe normalized audio input."""

    async def transcribe(self, audio: bytes, turn_id: UUID, token: CancellationToken) -> TranscriptSegment: ...

    def capabilities(self) -> CapabilityDescriptor: ...

    async def health(self) -> HealthStatus: ...


class TTSProvider(Protocol):
    """Synthesize normalized audio output."""

    async def synthesize(self, text: str, token: CancellationToken) -> bytes: ...

    def capabilities(self) -> CapabilityDescriptor: ...

    async def health(self) -> HealthStatus: ...


class DataStore(Protocol):
    """Persist normalized domain records."""

    def save_transcript(self, segment: TranscriptSegment) -> None: ...

    def list_transcript(self, session_id: UUID) -> list[TranscriptSegment]: ...

    def save_recording(self, recording: Recording) -> None: ...


class AuthProvider(Protocol):
    """Validate an authenticated user session."""

    async def validate(self, token: str) -> str: ...


class DocumentParser(Protocol):
    """Normalize untrusted document text."""

    def parse(self, content: bytes, content_type: str) -> str: ...


class EmbeddingProvider(Protocol):
    """Create embeddings for normalized content."""

    async def embed(self, text: str) -> list[float]: ...


class VectorStore(Protocol):
    """Store and retrieve document chunks."""

    def add(self, key: str, text: str, vector: list[float]) -> None: ...

    def search(self, vector: list[float], limit: int = 5) -> list[str]: ...


class AudioTransport(Protocol):
    """Abstract browser audio ingress and egress."""

    async def receive(self, token: CancellationToken) -> bytes: ...

    async def send(self, audio: bytes, token: CancellationToken) -> None: ...


class EventBus(Protocol):
    """Publish ordered domain lifecycle events."""

    async def publish(self, event: LifecycleEvent) -> None: ...


class StorageProvider(Protocol):
    """Store opaque sensitive files behind a provider boundary."""

    def put(self, key: str, content: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...


class ResearchProvider(Protocol):
    """Fetch attributed external context when explicitly enabled."""

    async def search(self, query: str, token: CancellationToken) -> list[dict[str, str]]: ...


class ObservabilityProvider(Protocol):
    """Record normalized provider measurements."""

    def record(self, measurement: object) -> None: ...
