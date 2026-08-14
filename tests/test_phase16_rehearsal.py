"""Tests for redacted Phase 16 rehearsal classification."""

import json
import tempfile
import unittest
from pathlib import Path

from interviewer_domain.phase16_rehearsal import Phase16Rehearsal, write_rehearsal_evidence


class Phase16RehearsalTests(unittest.TestCase):
    """Verify live evidence never claims unregistered operations succeeded."""

    def test_missing_configuration_is_skipped(self) -> None:
        """Absent live settings produce safe skips rather than false readiness."""
        results = Phase16Rehearsal(environ={}).run()
        self.assertTrue(all(result.status in {"skipped", "exercised"} for result in results))
        self.assertEqual(
            next(result for result in results if result.operation.marker == "beta-evidence-redacted-ok").status,
            "exercised",
        )
        self.assertEqual(len(results), 16)

    def test_configured_without_executor_fails(self) -> None:
        """Configured providers fail until a real live executor is supplied."""
        results = Phase16Rehearsal(
            environ={"LLM_API_KEY": "secret", "LLM_MODEL": "model"}
        ).run()
        llm = next(result for result in results if result.operation.marker == "llm-interviewer-stream-ok")
        self.assertEqual(llm.status, "failed")
        self.assertNotIn("secret", llm.reason)

    def test_evidence_is_redacted(self) -> None:
        """Evidence contains markers and statuses, never credential values."""
        with tempfile.TemporaryDirectory() as directory:
            results = Phase16Rehearsal(environ={}).run()
            output = write_rehearsal_evidence(directory, results)
            payload = json.loads(Path(output).read_text(encoding="utf-8"))
        serialized = json.dumps(payload)
        self.assertIn("phase16-live-beta-rehearsal", serialized)
        self.assertNotIn("resume text", serialized)
        self.assertNotIn("audio bytes", serialized)
        self.assertNotIn("api_key", serialized.lower())


if __name__ == "__main__":
    unittest.main()
