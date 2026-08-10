"""Behavior-level Phase 14 full user acceptance tests."""

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone

from interviewer_domain.contracts import ErrorCode, ProviderError
from interviewer_domain.e2e_acceptance import FORBIDDEN, MARKERS, run_local_acceptance_sync
from interviewer_domain.evaluation import InterviewContext, PostInterviewEvaluationService
from interviewer_domain.models import InterviewMode
from interviewer_domain.persistence import InMemoryPersistentDataStore, PersistenceService, UploadValidator
from interviewer_domain.providers import InMemoryStorage


class Phase14FullUserE2ETests(unittest.TestCase):
    """Exercise the repeatable local journey and its negative boundaries."""

    def test_full_local_user_journey_writes_observable_artifacts(self) -> None:
        """The local profile traverses API, media, providers, persistence, and evaluation."""
        report = run_local_acceptance_sync(".agent_tmp/phase14-test-evidence")
        self.assertTrue(report.passed, report.failures)
        self.assertEqual(report.markers, list(MARKERS))
        self.assertEqual({event.status for event in report.events}, {"passed"})
        paths = report.write(".agent_tmp/phase14-test-evidence")
        for path in paths:
            self.assertTrue(path.exists())
            self.assertNotIn("secret", path.read_text(encoding="utf-8").lower())

    def test_negative_journeys_use_real_boundaries(self) -> None:
        """Malformed PDF, owner access, and incomplete evaluation fail safely."""
        validator = UploadValidator()
        with self.assertRaises(ProviderError) as invalid_pdf:
            validator.validate_resume("resume.txt", b"not-pdf", "text/plain")
        self.assertEqual(invalid_pdf.exception.code, ErrorCode.INVALID_REQUEST)
        data = InMemoryPersistentDataStore()
        persistence = PersistenceService(data, InMemoryStorage())
        record = persistence.create_interview("candidate", InterviewMode.TECHNICAL, datetime.now(timezone.utc))
        with self.assertRaises(ProviderError):
            data.get_interview("other-user", record.id)
        with self.assertRaises(ProviderError):
            PostInterviewEvaluationService(data).evaluate(
                "candidate", record.id, InterviewContext(InterviewMode.TECHNICAL, "Engineer", "senior"), ()
            )

    def test_marker_output_is_complete_and_has_no_forbidden_diagnostics(self) -> None:
        """The executable marker stream is complete and clean."""
        report = run_local_acceptance_sync(".agent_tmp/phase14-marker-evidence")
        output = io.StringIO()
        with redirect_stdout(output):
            for marker in report.markers:
                print(marker)
        text = output.getvalue()
        self.assertEqual(text.splitlines(), list(MARKERS))
        self.assertFalse(any(pattern in text for pattern in FORBIDDEN))


if __name__ == "__main__":
    unittest.main()
