"""Behavior checks for the Phase 17 release gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_phase17_release_gate import GateResult, write_evidence


class Phase17ReleaseGateTests(unittest.TestCase):
    """Protect evidence shape and launch-blocker honesty."""

    def test_evidence_contains_results_and_blockers_without_secret_values(self) -> None:
        """Evidence is readable and does not include credential-shaped content."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_evidence(
                output,
                [GateResult("backend tests", "passed", "completed")],
                ("Browser identity remains unverified.",),
            )
            payload = json.loads((output / "phase17-release-gate.json").read_text())
            markdown = (output / "phase17-release-gate.md").read_text()

        self.assertEqual(payload["phase"], 17)
        self.assertEqual(payload["results"][0]["status"], "passed")
        self.assertEqual(payload["launch_blockers"], ["Browser identity remains unverified."])
        self.assertNotIn("Bearer ", markdown)
        self.assertNotIn("api_key", markdown.lower())


if __name__ == "__main__":
    unittest.main()
