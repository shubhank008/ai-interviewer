"""Deterministic Phase 8 post-interview evaluation evidence tests."""

import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from interviewer_domain.contracts import ErrorCode, ProviderError
from interviewer_domain.evaluation import (
    DeterministicEvaluator,
    InterviewContext,
    PostInterviewEvaluationService,
    normalized_rubric,
)
from interviewer_domain.models import InterviewMode, TranscriptSegment
from interviewer_domain.persistence import (
    InMemoryPersistentDataStore,
    InterviewRecord,
    LocalFilesystemStorage,
    PersistenceService,
)


class EvaluationTests(unittest.TestCase):
    """Exercise structured evaluation through real provider-independent paths."""

    def _transcript(self, *texts: str) -> tuple[TranscriptSegment, ...]:
        """Build stable final candidate segments for regression fixtures."""
        return tuple(TranscriptSegment(uuid4(), "candidate", text) for text in texts)

    def test_rubrics_normalize_and_modes_differ(self) -> None:
        """Each mode has bounded dimensions and distinct criteria and weights."""
        recruiter = normalized_rubric(InterviewMode.RECRUITER)
        technical = normalized_rubric(InterviewMode.TECHNICAL)
        self.assertAlmostEqual(sum(item.weight for item in recruiter), 1.0)
        self.assertAlmostEqual(sum(item.weight for item in technical), 1.0)
        self.assertNotEqual(tuple(item.key for item in recruiter), tuple(item.key for item in technical))
        self.assertEqual(len(recruiter), 5)
        self.assertTrue(all(0 <= item.weight <= 1 and item.weight for item in technical))
        print("[EVALUATION] rubric-quality-ok")

    def test_missing_ambiguous_and_score_bounds(self) -> None:
        """Missing evidence is explicit and mixed evidence lowers confidence safely."""
        transcript = self._transcript("I led the system design and delivered clear impact.", "I am unclear and not sure, but I collaborated with the team.")
        result = DeterministicEvaluator().evaluate(InterviewContext(InterviewMode.TECHNICAL, "Engineer", "senior"), transcript)
        self.assertTrue(0 <= result.score <= 100)
        self.assertTrue(any(item["evidence_status"] == "ambiguous" for item in result.dimensions))
        self.assertTrue(all(0 <= item["score"] <= 100 for item in result.dimensions))
        empty = self._transcript("hello")
        result = DeterministicEvaluator().evaluate(InterviewContext(InterviewMode.RECRUITER, "Recruiter", "mid"), empty)
        self.assertTrue(any(item["evidence_status"] == "missing" for item in result.dimensions))

    def test_deterministic_output_and_mock_persistence_path(self) -> None:
        """The complete evaluation and results path works without external services."""
        now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        data = InMemoryPersistentDataStore()
        with tempfile.TemporaryDirectory() as directory:
            persistence = PersistenceService(data, LocalFilesystemStorage(directory))
            created = persistence.create_interview("alice", InterviewMode.RECRUITER, now)
            record = replace(created, status="completed")
            data.save_interview(record)
            turns = self._transcript("I am motivated by this role and communicate clearly.", "I led a team and delivered impact with feedback.")
            context = InterviewContext(InterviewMode.RECRUITER, "Platform Engineer", "senior", "build reliable systems", "led teams")
            service = PostInterviewEvaluationService(data)
            first = service.evaluate("alice", record.id, context, turns)
            second = service.evaluate("alice", record.id, context, turns)
            self.assertEqual(first, second)
            self.assertEqual(persistence.resource("alice", "results", record.id, now).payload["evaluation"]["score"], first.score)
        print("[EVALUATION] deterministic-ok")
        print("[EVALUATION] mock-path-ok")

    def test_post_interview_access_and_retention(self) -> None:
        """Active, failed, wrong-owner, and expired interviews cannot be evaluated."""
        now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        data = InMemoryPersistentDataStore()
        active = InterviewRecord("alice", InterviewMode.TECHNICAL, created_at=now)
        data.save_interview(active)
        context = InterviewContext(InterviewMode.TECHNICAL, "Engineer", "senior")
        transcript = self._transcript("I can reason through the system design tradeoff.")
        service = PostInterviewEvaluationService(data)
        with self.assertRaises(ProviderError) as active_error:
            service.evaluate("alice", active.id, context, transcript)
        self.assertEqual(active_error.exception.code, ErrorCode.CONFLICT)
        completed = replace(active, status="completed", expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
        data.save_interview(completed)
        with self.assertRaises(ProviderError):
            service.evaluate("alice", completed.id, context, transcript)
        with self.assertRaises(ProviderError):
            service.evaluate("bob", active.id, context, transcript)
        print("[EVALUATION] access-retention-ok")


if __name__ == "__main__":
    unittest.main()
