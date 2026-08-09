"""Provider-independent browser communication contracts and local implementations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid4


class TransportValidationError(ValueError):
    """Raised when a browser transport payload violates its schema."""


class SessionEventType(StrEnum):
    """Control and state events delivered over the session WebSocket."""

    SESSION_STARTED = "session.started"
    SESSION_ACTIVE = "session.active"
    TRANSCRIPT_PARTIAL = "transcript.partial"
    TRANSCRIPT_FINAL = "transcript.final"
    PLAYBACK_STARTED = "playback.started"
    PLAYBACK_STOPPED = "playback.stopped"
    INTERRUPT_REQUESTED = "interrupt.requested"
    ERROR = "error"


class SignalingType(StrEnum):
    """WebRTC negotiation messages carried by the control channel."""

    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice_candidate"


@dataclass(frozen=True, slots=True)
class CreateSessionRequest:
    """Version one request for creating an interview session."""

    user_id: str
    mode: str

    def __post_init__(self) -> None:
        """Validate identity and supported mode values."""
        if not self.user_id.strip():
            raise TransportValidationError("user_id is required")
        if self.mode not in {"recruiter", "technical"}:
            raise TransportValidationError("mode is unsupported")

    def to_dict(self) -> dict[str, str]:
        """Return the wire representation of this request."""
        return {"user_id": self.user_id, "mode": self.mode}


@dataclass(frozen=True, slots=True)
class SessionResponse:
    """Version one response describing a browser session resource."""

    session_id: UUID
    user_id: str
    mode: str
    status: str
    websocket_path: str
    signaling_path: str

    def to_dict(self) -> dict[str, str]:
        """Return the wire representation of this response."""
        return {
            "id": str(self.session_id),
            "user_id": self.user_id,
            "mode": self.mode,
            "status": self.status,
            "websocket": self.websocket_path,
            "signaling": self.signaling_path,
        }


@dataclass(frozen=True, slots=True)
class SessionEvent:
    """An ordered, replayable WebSocket event for one interview session."""

    session_id: UUID
    sequence: int
    event_type: SessionEventType
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    idempotency_key: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Reject invalid sequence and correlation values."""
        if self.sequence < 1:
            raise TransportValidationError("event sequence must be positive")
        if not self.correlation_id.strip():
            raise TransportValidationError("correlation_id is required")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible event envelope."""
        return {
            "session_id": str(self.session_id),
            "sequence": self.sequence,
            "type": self.event_type.value,
            "payload": dict(self.payload),
            "correlation_id": self.correlation_id,
            "idempotency_key": self.idempotency_key,
        }


class SessionEventChannel(Protocol):
    """Publish and resume ordered control events for a session."""

    def publish(self, event_type: SessionEventType, payload: dict[str, Any], correlation_id: str) -> SessionEvent: ...

    def replay(self, session_id: UUID, after_sequence: int = 0) -> list[SessionEvent]: ...


class LocalSessionEventChannel:
    """Bounded in-memory event channel used by local and deterministic tests."""

    def __init__(self, session_id: UUID, retention: int = 256) -> None:
        """Create a channel for one session with bounded replay history."""
        if retention < 1:
            raise TransportValidationError("retention must be positive")
        self.session_id = session_id
        self._events: deque[SessionEvent] = deque(maxlen=retention)
        self._next_sequence = 0

    def publish(self, event_type: SessionEventType, payload: dict[str, Any], correlation_id: str, idempotency_key: str | None = None) -> SessionEvent:
        """Append one event or return the previously accepted idempotent event."""
        if not correlation_id.strip():
            raise TransportValidationError("correlation_id is required")
        key = idempotency_key or str(uuid4())
        for existing in self._events:
            if existing.idempotency_key == key:
                return existing
        self._next_sequence += 1
        event = SessionEvent(self.session_id, self._next_sequence, event_type, dict(payload), correlation_id, key)
        self._events.append(event)
        return event

    def replay(self, session_id: UUID, after_sequence: int = 0) -> list[SessionEvent]:
        """Replay events strictly newer than an acknowledged cursor."""
        if session_id != self.session_id:
            raise TransportValidationError("session correlation does not match channel")
        if after_sequence < 0 or after_sequence > self._next_sequence:
            raise TransportValidationError("replay cursor is invalid")
        return [event for event in self._events if event.sequence > after_sequence]


class BrowserControlTransport(Protocol):
    """Bidirectional non-media browser control transport."""

    async def send_event(self, event: SessionEvent) -> None: ...

    async def send_signaling(self, message: "SignalingMessage") -> None: ...


class BrowserMediaTransport(Protocol):
    """Bidirectional browser media-track transport, separate from control."""

    async def send_media(self, audio: bytes) -> None: ...

    async def receive_media(self) -> bytes: ...


@dataclass(frozen=True, slots=True)
class SignalingMessage:
    """Validated WebRTC signaling envelope with no media payload."""

    session_id: UUID
    message_type: SignalingType
    payload: dict[str, Any]
    correlation_id: str

    def __post_init__(self) -> None:
        """Validate signaling-specific required fields and forbid media bytes."""
        if not self.correlation_id.strip():
            raise TransportValidationError("signaling correlation_id is required")
        if any(key in self.payload for key in ("audio", "media", "audio_bytes")):
            raise TransportValidationError("signaling payload cannot contain media")
        required = {SignalingType.OFFER: "sdp", SignalingType.ANSWER: "sdp", SignalingType.ICE_CANDIDATE: "candidate"}
        if not isinstance(self.payload.get(required[self.message_type]), str) or not self.payload[required[self.message_type]].strip():
            raise TransportValidationError(f"{required[self.message_type]} is required")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible signaling envelope."""
        return {
            "session_id": str(self.session_id),
            "type": self.message_type.value,
            "payload": dict(self.payload),
            "correlation_id": self.correlation_id,
        }


class LocalWebRTCMediaTransport:
    """Deterministic media-track seam that never accepts control events."""

    def __init__(self) -> None:
        """Create an empty local media track buffer."""
        self._frames: deque[bytes] = deque()

    async def send_media(self, audio: bytes) -> None:
        """Send a non-empty media frame over the media seam."""
        if not audio:
            raise TransportValidationError("media frame is empty")
        self._frames.append(bytes(audio))

    async def receive_media(self) -> bytes:
        """Receive the oldest locally buffered media frame."""
        if not self._frames:
            raise TransportValidationError("no media frame available")
        return self._frames.popleft()


class LocalBrowserControlTransport:
    """Deterministic WebSocket-like control transport for events and signaling."""

    def __init__(self) -> None:
        """Create empty control message buffers."""
        self.events: list[SessionEvent] = []
        self.signaling: list[SignalingMessage] = []

    async def send_event(self, event: SessionEvent) -> None:
        """Record one control event without accepting media bytes."""
        self.events.append(event)

    async def send_signaling(self, message: SignalingMessage) -> None:
        """Record one validated signaling message on the control seam."""
        self.signaling.append(message)


class RestResourceCatalog:
    """Versioned REST resource paths and deterministic session bootstrap."""

    API_PREFIX = "/api/v1"

    @classmethod
    def session_collection(cls) -> str:
        """Return the versioned session collection path."""
        return f"{cls.API_PREFIX}/sessions"

    @classmethod
    def session(cls, session_id: UUID) -> str:
        """Return the versioned session resource path."""
        return f"{cls.session_collection()}/{session_id}"

    @classmethod
    def create_session(cls, request: CreateSessionRequest) -> SessionResponse:
        """Create a normalized local session response without external services."""
        session_id = uuid4()
        return SessionResponse(session_id, request.user_id, request.mode, "created", f"/ws/v1/sessions/{session_id}", f"{cls.session(session_id)}/signaling")
