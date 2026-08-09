"""Provider-independent domain values for interview records."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class InterviewMode(StrEnum):
    """Supported first-release interview modes."""

    RECRUITER = "recruiter"
    TECHNICAL = "technical"


class DocumentSource(StrEnum):
    """Trusted origin labels for candidate and role context."""

    JOB_DESCRIPTION = "job_description"
    RESUME = "resume"


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """A bounded, source-attributed piece of untrusted document text."""

    source: DocumentSource
    section: str
    text: str
    location: str
    trust_boundary: str = "untrusted_document"
    id: UUID = field(default_factory=uuid4)
    retention_days: int = 14


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    """Ranked document evidence returned to a topic-aware caller."""

    chunk: DocumentChunk
    score: float


class TurnState(StrEnum):
    """Lifecycle state for a voice turn."""

    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SessionStatus(StrEnum):
    """Lifecycle state for an interview session."""

    CREATED = "created"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class QuestionPlan:
    """A guarded, mode-specific candidate question plan."""

    session_id: UUID
    mode: InterviewMode
    topic: str
    prompt: str
    source_turn_sequence: int
    context_digest: str


@dataclass(frozen=True, slots=True)
class InterviewSession:
    """Identity and lifecycle metadata for one interview."""

    user_id: str
    mode: InterviewMode
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    status: str = "created"


@dataclass(frozen=True, slots=True)
class Turn:
    """A candidate or interviewer exchange in a voice-first session."""

    session_id: UUID
    sequence: int
    speaker: str
    input_audio: bytes = b""
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Reject invalid sequence numbers and speaker labels."""
        if self.sequence < 1:
            raise ValueError("turn sequence must be positive")
        if self.speaker not in {"candidate", "interviewer"}:
            raise ValueError("speaker must be candidate or interviewer")


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """A normalized, speaker-labeled transcript segment."""

    turn_id: UUID
    speaker: str
    text: str
    is_final: bool = True
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass(frozen=True, slots=True)
class Recording:
    """Metadata for persisted interview audio."""

    session_id: UUID
    storage_key: str
    content_type: str
    duration_ms: int | None = None


@dataclass(frozen=True, slots=True)
class Evaluation:
    """Versioned structured evaluation placeholder for post-interview use."""

    session_id: UUID
    rubric_version: str
    score: int | None = None
    dimensions: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        """Validate the optional score range."""
        if self.score is not None and not 0 <= self.score <= 100:
            raise ValueError("evaluation score must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class ProviderMeasurement:
    """Normalized timing, quality, cost, failure, and resource data."""

    capability: str
    provider: str
    operation: str
    latency_ms: int
    success: bool
    first_byte_latency_ms: int | None = None
    end_to_end_latency_ms: int | None = None
    quality: float | None = None
    estimated_cost: float = 0.0
    failure_code: str | None = None
    cpu_seconds: float | None = None
    memory_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    """Ordered event emitted while processing a domain operation."""

    session_id: UUID
    name: str
    sequence: int
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utc_now)
    correlation_id: str = ""
