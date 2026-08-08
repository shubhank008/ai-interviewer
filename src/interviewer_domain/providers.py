"""Deterministic in-memory providers for local development and tests."""

from collections import defaultdict
from uuid import UUID

from .contracts import (
    CancellationToken,
    CapabilityDescriptor,
    ErrorCode,
    HealthStatus,
    ProviderError,
)
from .models import LifecycleEvent, Recording, TranscriptSegment


class InMemorySTT:
    """Return configured transcript text for each audio payload."""

    def __init__(self, transcript: str = "I built a reliable service.") -> None:
        self.transcript = transcript

    async def transcribe(self, audio: bytes, turn_id: UUID, token: CancellationToken) -> TranscriptSegment:
        """Convert non-empty deterministic audio into a final segment."""
        token.raise_if_cancelled()
        if not audio:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "audio payload is empty")
        return TranscriptSegment(turn_id, "candidate", self.transcript)

    def capabilities(self) -> CapabilityDescriptor:
        """Describe this provider's supported behavior."""
        return CapabilityDescriptor("in-memory-stt", False, True)

    async def health(self) -> HealthStatus:
        """Return deterministic healthy status."""
        return HealthStatus(True)


class InMemoryLLM:
    """Return a deterministic interviewer response."""

    def __init__(self, response: str = "Thank you. Can you explain the impact?") -> None:
        self.response = response

    async def generate(self, prompt: str, token: CancellationToken) -> str:
        """Generate a response after checking cancellation and input."""
        token.raise_if_cancelled()
        if not prompt.strip():
            raise ProviderError(ErrorCode.INVALID_REQUEST, "prompt is empty")
        return self.response

    def capabilities(self) -> CapabilityDescriptor:
        """Describe this provider's supported behavior."""
        return CapabilityDescriptor("in-memory-llm", False, True)

    async def health(self) -> HealthStatus:
        """Return deterministic healthy status."""
        return HealthStatus(True)


class InMemoryTTS:
    """Encode deterministic speech-shaped bytes without audio dependencies."""

    async def synthesize(self, text: str, token: CancellationToken) -> bytes:
        """Return a stable byte representation for non-empty text."""
        token.raise_if_cancelled()
        if not text.strip():
            raise ProviderError(ErrorCode.INVALID_REQUEST, "text is empty")
        return b"WAV-MOCK:" + text.encode("utf-8")

    def capabilities(self) -> CapabilityDescriptor:
        """Describe this provider's supported behavior."""
        return CapabilityDescriptor("in-memory-tts", False, True)

    async def health(self) -> HealthStatus:
        """Return deterministic healthy status."""
        return HealthStatus(True)


class InMemoryDataStore:
    """Store transcript and recording values in process memory."""

    def __init__(self) -> None:
        self.transcripts: dict[UUID, list[TranscriptSegment]] = defaultdict(list)
        self.recordings: dict[UUID, Recording] = {}
        self._turn_sessions: dict[UUID, UUID] = {}

    def link_turn_session(self, turn_id: UUID, session_id: UUID) -> None:
        """Register the mapping from a turn to its owning session."""
        self._turn_sessions[turn_id] = session_id

    def save_transcript(self, segment: TranscriptSegment) -> None:
        """Append a transcript segment by its turn identifier."""
        self.transcripts[segment.turn_id].append(segment)

    def list_transcript(self, session_id: UUID) -> list[TranscriptSegment]:
        """Return segments whose turns belong to the given session."""
        return [
            segment
            for turn_id, segments in self.transcripts.items()
            if self._turn_sessions.get(turn_id) == session_id
            for segment in segments
        ]

    def save_recording(self, recording: Recording) -> None:
        """Store recording metadata by session identifier."""
        self.recordings[recording.session_id] = recording


class InMemoryEventBus:
    """Collect lifecycle events in publish order."""

    def __init__(self) -> None:
        self.events: list[LifecycleEvent] = []

    async def publish(self, event: LifecycleEvent) -> None:
        """Append one lifecycle event."""
        self.events.append(event)


class InMemoryStorage:
    """Store opaque bytes and content types in memory."""

    def __init__(self) -> None:
        self.files: dict[str, tuple[bytes, str]] = {}

    def put(self, key: str, content: bytes, content_type: str) -> None:
        """Store content under a caller-owned key."""
        self.files[key] = (content, content_type)

    def get(self, key: str) -> bytes:
        """Retrieve content or raise the normalized unavailable error."""
        try:
            return self.files[key][0]
        except KeyError as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "storage key not found") from exc