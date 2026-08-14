"""Deterministic Phase 7 persistence and identity evidence tests."""

import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from interviewer_domain.contracts import ErrorCode, ProviderError
from interviewer_domain.models import (
    Evaluation,
    InterviewMode,
    Recording,
    TranscriptSegment,
)
from interviewer_domain.persistence import (
    FirebaseAuthAdapter,
    FirestoreDataStore,
    FixedWindowRateLimiter,
    InMemoryAuthProvider,
    InMemoryPersistentDataStore,
    InterviewRecord,
    LocalFilesystemStorage,
    PersistenceService,
    S3CompatibleStorage,
    UploadValidator,
    UserIdentity,
)


class FakeAuthBackend:
    """Backend fixture for the Firebase adapter seam."""

    def verify(self, token: str) -> dict[str, str]:
        """Return normalized Firebase-like claims."""
        return {"uid": token.removeprefix("firebase:")}


class FakeFirestoreBackend:
    """Backend fixture for the Firestore adapter seam."""

    def __init__(self) -> None:
        self.values: dict[tuple[str, str], dict] = {}

    def set(self, collection: str, document_id: str, value: dict) -> None:
        """Store a provider-shaped document."""
        self.values[(collection, document_id)] = value

    def get(self, collection: str, document_id: str) -> dict | None:
        """Read a provider-shaped document."""
        return self.values.get((collection, document_id))

    def list(self, collection: str, field: str, value: str) -> list[dict]:
        """List documents matching one owner field."""
        return [item for (name, _), item in self.values.items() if name == collection and item.get(field) == value]

    def delete_collection_value(self, collection: str, field: str, value: str) -> None:
        """Delete matching documents from the fixture."""
        for key, item in list(self.values.items()):
            if key[0] == collection and item.get(field) == value:
                del self.values[key]

    def delete_collection(self, collection: str) -> None:
        """Delete every document stored under one collection name."""
        for key in list(self.values):
            if key[0] == collection:
                del self.values[key]


class FakeObjectBackend:
    """Backend fixture for the S3-compatible storage seam."""

    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def put_object(self, key: str, content: bytes, content_type: str) -> None:
        """Store bytes while ignoring transport-specific metadata."""
        self.values[key] = content

    def get_object(self, key: str) -> bytes:
        """Return an object or raise a backend-shaped not-found error."""
        return self.values[key]

    def delete_prefix(self, prefix: str) -> None:
        """Delete all keys under a prefix."""
        for key in list(self.values):
            if key.startswith(prefix):
                del self.values[key]


class PersistenceTests(unittest.TestCase):
    """Exercise provider seams and the complete local persistence path."""

    def test_auth_and_adapters(self) -> None:
        """Validate identities and exercise local, remote, and Firebase seams."""
        self.assertEqual(asyncio.run(InMemoryAuthProvider({"t": UserIdentity("alice")}).validate("t")), "alice")
        self.assertEqual(asyncio.run(FirebaseAuthAdapter(FakeAuthBackend()).validate("firebase:bob")), "bob")
        with tempfile.TemporaryDirectory() as directory:
            local = LocalFilesystemStorage(directory)
            local.put("users/alice/file", b"data", "text/plain")
            self.assertEqual(local.get("users/alice/file"), b"data")
            with self.assertRaises(ProviderError):
                local.get("../outside")
        firestore_backend = FakeFirestoreBackend()
        firestore = FirestoreDataStore(firestore_backend)
        firestore_record = InterviewRecord("alice", InterviewMode.RECRUITER, created_at=datetime(2027, 1, 1, tzinfo=timezone.utc)).with_retention()
        firestore.save_interview(firestore_record)
        self.assertEqual(firestore.get_interview("alice", firestore_record.id).id, firestore_record.id)
        self.assertEqual(len(firestore.list_interviews("alice", datetime(2027, 1, 2, tzinfo=timezone.utc))), 1)
        remote = FakeObjectBackend()
        cloud = S3CompatibleStorage(remote)
        cloud.put("users/alice/file", b"data", "text/plain")
        self.assertEqual(cloud.get("users/alice/file"), b"data")
        print("[PERSISTENCE] adapters-ok")

    def test_firestore_complete_deletion(self) -> None:
        """Remove every Firestore document category, not only the top-level record."""
        firestore_backend = FakeFirestoreBackend()
        firestore = FirestoreDataStore(firestore_backend)
        record = InterviewRecord("alice", InterviewMode.RECRUITER, created_at=datetime(2027, 1, 1, tzinfo=timezone.utc)).with_retention()
        firestore.save_interview(record)
        firestore.save_transcript("alice", record.id, TranscriptSegment(uuid4(), "candidate", "hello"))
        firestore.save_recording("alice", record.id, Recording(record.id, "users/alice/interviews/audio", "audio/wav"))
        firestore.save_evaluation("alice", record.id, Evaluation(record.id, "v1", 80))
        firestore.save_document_reference("alice", record.id, "users/alice/interviews/document")
        self.assertEqual(len(firestore_backend.values), 5)
        firestore.delete_interview("alice", record.id)
        self.assertEqual(firestore_backend.values, {})
        print("[PERSISTENCE] firestore-complete-deletion-ok")

    def test_authorization_retention_and_complete_deletion(self) -> None:
        """Keep owners isolated and remove all categories on deletion."""
        now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        data = InMemoryPersistentDataStore()
        with tempfile.TemporaryDirectory() as directory:
            service = PersistenceService(data, LocalFilesystemStorage(directory))
            record = service.create_interview("alice", InterviewMode.RECRUITER, now)
            with self.assertRaises(ProviderError) as error:
                data.get_interview("bob", record.id)
            self.assertEqual(error.exception.code, ErrorCode.UNAVAILABLE)
            segment = TranscriptSegment(uuid4(), "candidate", "hello")
            data.save_transcript("alice", record.id, segment)
            data.save_recording("alice", record.id, Recording(record.id, "users/alice/interviews/audio", "audio/wav"))
            data.save_evaluation("alice", record.id, Evaluation(record.id, "v1", 80))
            data.save_document_reference("alice", record.id, "users/alice/interviews/document")
            service.delete_interview("alice", record.id)
            self.assertNotIn(record.id, data.interviews)
            self.assertNotIn(record.id, data.transcripts)
            self.assertNotIn(record.id, data.recordings)
            self.assertNotIn(record.id, data.evaluations)
            expired = service.create_interview("alice", InterviewMode.TECHNICAL, now - timedelta(days=15))
            self.assertEqual(data.purge_expired(now), [expired.id])
        print("[PERSISTENCE] auth-isolation-ok")
        print("[PERSISTENCE] retention-deletion-ok")

    def test_upload_and_rate_limit(self) -> None:
        """Reject unsafe uploads and enforce a deterministic request window."""
        validator = UploadValidator()
        upload = validator.validate_resume("resume.pdf", b"%PDF-1.7 resume", "application/pdf")
        self.assertEqual(upload.content_type, "application/pdf")
        with self.assertRaises(ProviderError):
            validator.validate_resume("resume.txt", b"%PDF-1.7", "application/pdf")
        with self.assertRaises(ProviderError):
            validator.validate_resume("resume.pdf", b"not-pdf", "application/pdf")
        with self.assertRaises(ProviderError):
            validator.validate_resume("resume.pdf", b"%PDF" + b"x" * (10 * 1024 * 1024 + 1), "application/pdf")
        limiter = FixedWindowRateLimiter(limit=2, window_seconds=60)
        self.assertTrue(limiter.allow("alice", datetime(2027, 1, 1, tzinfo=timezone.utc)))
        self.assertTrue(limiter.allow("alice", datetime(2027, 1, 1, tzinfo=timezone.utc)))
        self.assertFalse(limiter.allow("alice", datetime(2027, 1, 1, tzinfo=timezone.utc)))
        print("[PERSISTENCE] upload-rate-limit-ok")

    def test_real_mock_persistence_and_ux_contracts(self) -> None:
        """Exercise setup, artifact persistence, history, and UI resource contracts."""
        now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        data = InMemoryPersistentDataStore()
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalFilesystemStorage(Path(directory))
            service = PersistenceService(data, storage)
            record = service.create_interview("alice", InterviewMode.TECHNICAL, now)
            artifact = service.save_upload("alice", record.id, UploadValidator().validate_resume("resume.pdf", b"%PDF-resume", "application/pdf"), now)
            data.save_transcript("alice", record.id, TranscriptSegment(uuid4(), "candidate", "I designed it."))
            self.assertEqual(storage.get(artifact.key), b"%PDF-resume")
            self.assertEqual(len(service.resource("alice", "history", now=now).payload["interviews"]), 1)
            for view in ("setup", "active", "replay", "transcript", "results"):
                self.assertEqual(service.resource("alice", view, record.id, now=now).view, view)
        print("[PERSISTENCE] mock-persistence-ok")
        print("[PERSISTENCE] ux-contracts-ok")


if __name__ == "__main__":
    unittest.main()
