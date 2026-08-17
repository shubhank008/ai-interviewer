"""Provider-independent identity, persistence, retention, and storage services."""

from __future__ import annotations

import hashlib
import mimetypes
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from uuid import UUID, uuid4

from ..contracts import ErrorCode, ProviderError
from ..models import Evaluation, InterviewMode, Recording, TranscriptSegment

DEFAULT_RETENTION_DAYS = 14
MAX_RESUME_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """Normalized authenticated identity claims."""

    user_id: str
    email: str | None = None
    claims: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class InterviewRecord:
    """Minimal durable interview metadata with an explicit owner and expiry."""

    user_id: str
    mode: InterviewMode
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    status: str = "created"
    end_reason: str | None = None
    end_rationale: str = ""

    def with_retention(self, days: int = DEFAULT_RETENTION_DAYS) -> InterviewRecord:
        """Return this record with a deterministic retention boundary."""
        if days < 1:
            raise ValueError("retention days must be positive")
        return InterviewRecord(
            self.user_id,
            self.mode,
            self.id,
            self.created_at,
            self.created_at + timedelta(days=days),
            self.status,
            self.end_reason,
            self.end_rationale,
        )


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    """Metadata for an opaque user-owned file."""

    interview_id: UUID
    user_id: str
    key: str
    content_type: str
    size: int
    sha256: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class Upload:
    """Validated upload input before it crosses a storage boundary."""

    filename: str
    content: bytes
    content_type: str


@dataclass(frozen=True, slots=True)
class UXResource:
    """Stable UI-independent resource contract for a named user view."""

    view: str
    interview_id: UUID | None
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize a view resource using JSON-safe values."""
        return {
            "view": self.view,
            "interview_id": str(self.interview_id) if self.interview_id else None,
            "payload": self.payload,
        }


class AuthBackend(Protocol):
    """Small backend seam for a hosted identity provider."""

    def verify(self, token: str) -> dict[str, Any]: ...


class FirestoreBackend(Protocol):
    """Small document backend seam used by the Firestore adapter."""

    def set(self, collection: str, document_id: str, value: dict[str, Any]) -> None: ...
    def get(self, collection: str, document_id: str) -> dict[str, Any] | None: ...
    def list(self, collection: str, field: str, value: str) -> list[dict[str, Any]]: ...
    def list_all(self, collection: str) -> list[dict[str, Any]]: ...
    def delete_collection_value(
        self, collection: str, field: str, value: str
    ) -> None: ...
    def delete_collection(self, collection: str) -> None: ...
    def delete_document(self, collection: str, document_id: str) -> None: ...


class ObjectBackend(Protocol):
    """Small object backend seam for S3-compatible storage."""

    def put_object(self, key: str, content: bytes, content_type: str) -> None: ...
    def get_object(self, key: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> None: ...


class PersistentDataStore(Protocol):
    """Durable data capability needed by the Phase 7 service."""

    def save_interview(self, record: InterviewRecord) -> None: ...
    def get_interview(self, user_id: str, interview_id: UUID) -> InterviewRecord: ...
    def list_interviews(self, user_id: str, now: datetime) -> list[InterviewRecord]: ...
    def save_transcript(
        self, user_id: str, interview_id: UUID, segment: TranscriptSegment
    ) -> None: ...
    def list_transcripts(
        self, user_id: str, interview_id: UUID
    ) -> list[TranscriptSegment]: ...
    def save_recording(
        self, user_id: str, interview_id: UUID, recording: Recording
    ) -> None: ...
    def save_evaluation(
        self, user_id: str, interview_id: UUID, evaluation: Evaluation
    ) -> None: ...
    def get_evaluation(self, user_id: str, interview_id: UUID) -> Evaluation | None: ...
    def save_document_reference(
        self, user_id: str, interview_id: UUID, key: str
    ) -> None: ...
    def delete_interview(self, user_id: str, interview_id: UUID) -> None: ...
    def expired_interviews(self, now: datetime) -> list[InterviewRecord]: ...


class PersistentStorageProvider(Protocol):
    """Durable opaque-file capability needed by the Phase 7 service."""

    def put(self, key: str, content: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> None: ...


class InMemoryAuthProvider:
    """Deterministic token identity provider for local tests."""

    def __init__(self, tokens: dict[str, UserIdentity] | None = None) -> None:
        self.tokens = tokens or {}

    async def validate(self, token: str) -> str:
        """Resolve a token to an opaque user ID without exposing claims."""
        try:
            return self.tokens[token].user_id
        except KeyError as exc:
            raise ProviderError(
                ErrorCode.INVALID_REQUEST, "invalid authentication token"
            ) from exc


class FirebaseAuthAdapter:
    """Firebase Authentication adapter using an injected verification backend."""

    def __init__(self, backend: AuthBackend) -> None:
        self.backend = backend

    async def validate(self, token: str) -> str:
        """Verify a Firebase token while keeping SDK details outside the domain."""
        if not token:
            raise ProviderError(
                ErrorCode.INVALID_REQUEST, "authentication token is empty"
            )
        try:
            claims = self.backend.verify(token)
            user_id = str(claims["uid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(
                ErrorCode.INVALID_REQUEST, "invalid authentication token"
            ) from exc
        if not user_id:
            raise ProviderError(
                ErrorCode.INVALID_REQUEST, "authentication identity is empty"
            )
        return user_id


class InMemoryPersistentDataStore:
    """Complete deterministic data store for the real mock persistence path."""

    def __init__(self) -> None:
        self.interviews: dict[UUID, InterviewRecord] = {}
        self.transcripts: dict[UUID, list[TranscriptSegment]] = {}
        self.recordings: dict[UUID, Recording] = {}
        self.evaluations: dict[UUID, Evaluation] = {}
        self.documents: dict[UUID, list[str]] = {}

    def save_interview(self, record: InterviewRecord) -> None:
        """Save an interview metadata record."""
        self.interviews[record.id] = record

    def get_interview(
        self, user_id: str, interview_id: UUID, now: datetime | None = None
    ) -> InterviewRecord:
        """Return an owned, non-expired interview or a safe not-found error."""
        record = self.interviews.get(interview_id)
        current = now or datetime.now(timezone.utc)
        if (
            record is None
            or record.user_id != user_id
            or (record.expires_at is not None and record.expires_at <= current)
        ):
            raise ProviderError(ErrorCode.UNAVAILABLE, "interview not found")
        return record

    def list_interviews(self, user_id: str, now: datetime) -> list[InterviewRecord]:
        """List only owned records that remain within their retention boundary."""
        return [
            r
            for r in self.interviews.values()
            if r.user_id == user_id and (r.expires_at is None or r.expires_at > now)
        ]

    def save_transcript(
        self, user_id: str, interview_id: UUID, segment: TranscriptSegment
    ) -> None:
        """Persist a transcript segment after checking interview ownership."""
        self.get_interview(user_id, interview_id)
        self.transcripts.setdefault(interview_id, []).append(segment)

    def list_transcripts(
        self, user_id: str, interview_id: UUID
    ) -> list[TranscriptSegment]:
        """Return owned transcript segments for an interview."""
        self.get_interview(user_id, interview_id)
        return list(self.transcripts.get(interview_id, []))

    def save_recording(
        self, user_id: str, interview_id: UUID, recording: Recording
    ) -> None:
        """Persist recording metadata after checking interview ownership."""
        self.get_interview(user_id, interview_id)
        self.recordings[interview_id] = recording

    def save_evaluation(
        self, user_id: str, interview_id: UUID, evaluation: Evaluation
    ) -> None:
        """Persist evaluation metadata after checking interview ownership."""
        self.get_interview(user_id, interview_id)
        self.evaluations[interview_id] = evaluation

    def get_evaluation(
        self, user_id: str, interview_id: UUID, now: datetime | None = None
    ) -> Evaluation | None:
        """Return an owned, non-expired interview evaluation or None when absent."""
        record = self.interviews.get(interview_id)
        current = now or datetime.now(timezone.utc)
        if (
            record is None
            or record.user_id != user_id
            or (record.expires_at is not None and record.expires_at <= current)
        ):
            return None
        return self.evaluations.get(interview_id)

    def save_document_reference(
        self, user_id: str, interview_id: UUID, key: str
    ) -> None:
        """Persist a document storage reference after checking ownership."""
        self.get_interview(user_id, interview_id)
        self.documents.setdefault(interview_id, []).append(key)

    def delete_interview(self, user_id: str, interview_id: UUID) -> None:
        """Delete every data category belonging to one owned interview, including expired data."""
        record = self.interviews.get(interview_id)
        if record is None or record.user_id != user_id:
            raise ProviderError(ErrorCode.UNAVAILABLE, "interview not found")
        self.interviews.pop(interview_id, None)
        self.transcripts.pop(interview_id, None)
        self.recordings.pop(interview_id, None)
        self.evaluations.pop(interview_id, None)
        self.documents.pop(interview_id, None)

    def expired_interviews(self, now: datetime) -> list[InterviewRecord]:
        """Return expired records with owners preserved for scoped deletion."""
        return [
            record
            for record in self.interviews.values()
            if record.expires_at is not None and record.expires_at <= now
        ]

    def purge_expired(self, now: datetime) -> list[UUID]:
        """Delete expired metadata and dependent in-store records."""
        expired = self.expired_interviews(now)
        for record in expired:
            self.interviews.pop(record.id, None)
            self.transcripts.pop(record.id, None)
            self.recordings.pop(record.id, None)
            self.evaluations.pop(record.id, None)
            self.documents.pop(record.id, None)
        return [record.id for record in expired]


class FirestoreDataStore:
    """Firestore adapter using an injected document backend and normalized records."""

    def __init__(
        self, backend: FirestoreBackend, collection: str = "interviews"
    ) -> None:
        self.backend = backend
        self.collection = collection

    def save_interview(self, record: InterviewRecord) -> None:
        """Write a normalized interview document."""
        self.backend.set(self.collection, str(record.id), _json_record(record))

    def get_interview(
        self, user_id: str, interview_id: UUID, now: datetime | None = None
    ) -> InterviewRecord:
        """Read and authorize one Firestore interview document."""
        value = self.backend.get(self.collection, str(interview_id))
        record = _record_from_json(value) if value is not None else None
        current = now or datetime.now(timezone.utc)
        if (
            record is None
            or record.user_id != user_id
            or (record.expires_at is not None and record.expires_at <= current)
        ):
            raise ProviderError(ErrorCode.UNAVAILABLE, "interview not found")
        return record

    def list_interviews(self, user_id: str, now: datetime) -> list[InterviewRecord]:
        """List owned, non-expired Firestore interview documents."""
        return [
            r
            for r in (
                _record_from_json(v)
                for v in self.backend.list(self.collection, "user_id", user_id)
            )
            if r.expires_at is None or r.expires_at > now
        ]

    def expired_interviews(self, now: datetime) -> list[InterviewRecord]:
        """Return expired Firestore records for owner-scoped cleanup."""
        return [
            record
            for record in (
                _record_from_json(value)
                for value in self.backend.list_all(self.collection)
            )
            if record.expires_at is not None and record.expires_at <= now
        ]

    def save_transcript(
        self, user_id: str, interview_id: UUID, segment: TranscriptSegment
    ) -> None:
        """Persist a transcript in the interview subcollection."""
        self.get_interview(user_id, interview_id)
        payload = _firestore_safe(asdict(segment))
        payload["user_id"] = user_id
        self.backend.set(
            f"{self.collection}/{interview_id}/transcripts",
            str(uuid4()),
            payload,
        )

    def list_transcripts(
        self, user_id: str, interview_id: UUID
    ) -> list[TranscriptSegment]:
        """Return owned transcript segments from the Firestore subcollection."""
        self.get_interview(user_id, interview_id)
        subcollection = f"{self.collection}/{interview_id}/transcripts"
        return [
            TranscriptSegment(
                turn_id=UUID(str(doc["turn_id"])),
                speaker=str(doc["speaker"]),
                text=str(doc["text"]),
                is_final=bool(doc.get("is_final", True)),
                start_ms=int(doc["start_ms"])
                if doc.get("start_ms") is not None
                else None,
                end_ms=int(doc["end_ms"]) if doc.get("end_ms") is not None else None,
            )
            for doc in self.backend.list(subcollection, "user_id", user_id)
        ]

    def save_recording(
        self, user_id: str, interview_id: UUID, recording: Recording
    ) -> None:
        """Persist recording metadata in the interview document."""
        self.get_interview(user_id, interview_id)
        self.backend.set(
            f"{self.collection}/{interview_id}/recordings",
            "current",
            _firestore_safe(asdict(recording)),
        )

    def save_evaluation(
        self, user_id: str, interview_id: UUID, evaluation: Evaluation
    ) -> None:
        """Persist evaluation metadata in the interview document."""
        self.get_interview(user_id, interview_id)
        self.backend.set(
            f"{self.collection}/{interview_id}/evaluations",
            "current",
            _firestore_safe(asdict(evaluation)),
        )

    def get_evaluation(self, user_id: str, interview_id: UUID) -> Evaluation | None:
        """Return an owned evaluation document or None when absent."""
        self.get_interview(user_id, interview_id)
        value = self.backend.get(f"{self.collection}/{interview_id}/evaluations", "current")
        return _evaluation_from_json(value) if value is not None else None

    def save_document_reference(
        self, user_id: str, interview_id: UUID, key: str
    ) -> None:
        """Persist an opaque document reference for an owned interview."""
        self.get_interview(user_id, interview_id)
        self.backend.set(
            f"{self.collection}/{interview_id}/documents", "current", {"key": key}
        )

    def delete_interview(self, user_id: str, interview_id: UUID) -> None:
        """Delete all Firestore documents and subcollections for an owned interview, including expired data."""
        value = self.backend.get(self.collection, str(interview_id))
        if value is None or value.get("user_id") != user_id:
            raise ProviderError(ErrorCode.UNAVAILABLE, "interview not found")
        delete_document = getattr(self.backend, "delete_document", None)
        if delete_document is not None:
            delete_document(self.collection, str(interview_id))
        else:
            self.backend.delete_collection_value(self.collection, "id", str(interview_id))
        for subcollection in ("transcripts", "recordings", "evaluations", "documents"):
            self.backend.delete_collection(f"{self.collection}/{interview_id}/{subcollection}")


class LocalFilesystemStorage:
    """Filesystem storage rooted in a local directory or Docker volume."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        """Resolve a safe relative key below the configured root."""
        path = (self.root / PurePosixPath(key)).resolve()
        if self.root not in path.parents:
            raise ProviderError(
                ErrorCode.INVALID_REQUEST, "storage key escapes storage root"
            )
        return path

    def put(self, key: str, content: bytes, content_type: str) -> None:
        """Write bytes and a small content-type sidecar atomically enough for local use."""
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.with_suffix(path.suffix + ".content-type").write_text(
            content_type, encoding="utf-8"
        )

    def get(self, key: str) -> bytes:
        """Read an object or return a normalized not-found error."""
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "storage key not found") from exc

    def delete_prefix(self, prefix: str) -> None:
        """Delete all objects under an interview prefix."""
        path = self._path(prefix)
        if path.exists():
            shutil.rmtree(path) if path.is_dir() else path.unlink()


class S3CompatibleStorage:
    """S3-compatible adapter using an injected object client."""

    def __init__(self, backend: ObjectBackend) -> None:
        self.backend = backend

    def put(self, key: str, content: bytes, content_type: str) -> None:
        """Delegate object upload without importing an S3 SDK."""
        self.backend.put_object(key, content, content_type)

    def get(self, key: str) -> bytes:
        """Read an object and normalize backend lookup failures."""
        try:
            return self.backend.get_object(key)
        except KeyError as exc:
            raise ProviderError(ErrorCode.UNAVAILABLE, "storage key not found") from exc

    def delete_prefix(self, prefix: str) -> None:
        """Delete all objects under an interview prefix."""
        self.backend.delete_prefix(prefix)


class UploadValidator:
    """Validate untrusted resume uploads before persistence."""

    def validate_resume(
        self, filename: str, content: bytes, content_type: str | None = None
    ) -> Upload:
        """Require a PDF signature, PDF-like name, and the configured size bound."""
        if len(content) > MAX_RESUME_BYTES:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "resume exceeds 10 MB limit")
        if not filename.lower().endswith(".pdf") or not content.startswith(b"%PDF"):
            raise ProviderError(ErrorCode.INVALID_REQUEST, "resume must be a PDF")
        normalized_type = (
            content_type or mimetypes.guess_type(filename)[0] or "application/pdf"
        )
        if normalized_type != "application/pdf":
            raise ProviderError(
                ErrorCode.INVALID_REQUEST, "resume content type must be application/pdf"
            )
        return Upload(filename, content, normalized_type)


class FixedWindowRateLimiter:
    """Deterministic per-key fixed-window request limiter."""

    def __init__(self, limit: int = 60, window_seconds: int = 60) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("rate-limit values must be positive")
        self.limit = limit
        self.window = timedelta(seconds=window_seconds)
        self._state: dict[str, tuple[datetime, int]] = {}

    def allow(self, key: str, now: datetime) -> bool:
        """Return whether this request remains within the current window."""
        started, count = self._state.get(key, (now, 0))
        if now - started >= self.window:
            started, count = now, 0
        if count >= self.limit:
            self._state[key] = (started, count)
            return False
        self._state[key] = (started, count + 1)
        return True


class PersistenceService:
    """Coordinate ownership, retention, artifacts, and UI resource contracts."""

    def __init__(
        self,
        data: PersistentDataStore,
        storage: PersistentStorageProvider,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> None:
        self.data = data
        self.storage = storage
        self.retention_days = retention_days

    def create_interview(
        self, user_id: str, mode: InterviewMode, now: datetime
    ) -> InterviewRecord:
        """Create an owned interview with an explicit retention boundary."""
        record = InterviewRecord(user_id, mode, created_at=now).with_retention(
            self.retention_days
        )
        self.data.save_interview(record)
        return record

    def save_upload(
        self, user_id: str, interview_id: UUID, upload: Upload, now: datetime
    ) -> StoredArtifact:
        """Store a validated upload under an owner and interview scoped key."""
        record = self.data.get_interview(user_id, interview_id)
        key = f"users/{user_id}/interviews/{interview_id}/documents/{uuid4()}-{upload.filename}"
        self.storage.put(key, upload.content, upload.content_type)
        self.data.save_document_reference(user_id, interview_id, key)
        return StoredArtifact(
            interview_id,
            user_id,
            key,
            upload.content_type,
            len(upload.content),
            hashlib.sha256(upload.content).hexdigest(),
            record.expires_at or now + timedelta(days=self.retention_days),
        )

    def delete_interview(self, user_id: str, interview_id: UUID) -> None:
        """Delete metadata and all opaque files for one authorized interview."""
        self.storage.delete_prefix(f"users/{user_id}/interviews/{interview_id}")
        self.data.delete_interview(user_id, interview_id)

    def purge_expired(self, now: datetime | None = None) -> list[UUID]:
        """Delete expired interviews and their owner-scoped storage artifacts."""
        current = now or datetime.now(timezone.utc)
        expired = self.data.expired_interviews(current)
        for record in expired:
            self.delete_interview(record.user_id, record.id)
        return [record.id for record in expired]

    def resource(
        self,
        user_id: str,
        view: str,
        interview_id: UUID | None = None,
        now: datetime | None = None,
    ) -> UXResource:
        """Build provider-neutral setup, active, replay, transcript, or results data."""
        current = now or datetime.now(timezone.utc)
        if view == "history":
            return UXResource(
                view,
                None,
                {
                    "interviews": [
                        _json_record(r)
                        for r in self.data.list_interviews(user_id, current)
                    ]
                },
            )
        if interview_id is None:
            return UXResource(view, None, {"user_id": user_id})
        record = self.data.get_interview(user_id, interview_id)
        payload: dict[str, Any] = {
            "interview": _json_record(record),
            "available": view in {"active", "replay", "transcript", "results"},
        }
        if view == "results":
            evaluation = self.data.get_evaluation(user_id, interview_id)
            if evaluation is not None:
                from ..evaluation import evaluation_dict

                payload["evaluation"] = evaluation_dict(evaluation)
        return UXResource(view, interview_id, payload)


def _firestore_safe(value: Any) -> Any:
    """Convert domain values into Firestore-supported primitive containers."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _firestore_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_firestore_safe(item) for item in value]
    return value


def _json_record(record: InterviewRecord) -> dict[str, Any]:
    """Convert normalized metadata into a JSON-safe dictionary."""
    value = asdict(record)
    value["id"] = str(record.id)
    value["mode"] = record.mode.value
    value["created_at"] = record.created_at.isoformat()
    value["expires_at"] = record.expires_at.isoformat() if record.expires_at else None
    return value


def _record_from_json(value: dict[str, Any]) -> InterviewRecord:
    """Restore normalized metadata from a provider document."""
    return InterviewRecord(
        str(value["user_id"]),
        InterviewMode(value["mode"]),
        UUID(str(value["id"])),
        datetime.fromisoformat(value["created_at"]),
        datetime.fromisoformat(value["expires_at"])
        if value.get("expires_at")
        else None,
        str(value.get("status", "created")),
        str(value.get("end_reason")) if value.get("end_reason") is not None else None,
        str(value.get("end_rationale", "")),
    )


def _evaluation_from_json(value: dict[str, Any]) -> Evaluation:
    """Restore an evaluation document from a provider store."""
    return Evaluation(
        UUID(str(value["session_id"])),
        str(value["rubric_version"]),
        int(value["score"]) if value.get("score") is not None else None,
        tuple(entry for entry in value.get("dimensions", ())),
        str(value.get("mode", "")),
        dict(value.get("context", {})),
        str(value.get("summary", "")),
        tuple(value.get("strengths", ())),
        tuple(value.get("weaknesses", ())),
        tuple(value.get("recommendations", ())),
    )
