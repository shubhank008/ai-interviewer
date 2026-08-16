"""Tests for redacted Phase 16 rehearsal classification."""

import json
import tempfile
import unittest
from pathlib import Path

from interviewer_domain.phase16_rehearsal import Phase16Rehearsal, write_rehearsal_evidence, write_rehearsal_transcript
from interviewer_domain.adapters.persistence import InMemoryPersistentDataStore
from interviewer_domain.evaluation import DeterministicEvaluator
from interviewer_domain.models import InterviewMode, TranscriptSegment
from interviewer_domain.phase16_rehearsal import (
    IntervieweeAgent,
    InterviewerAgent,
    RehearsalProviders,
    load_dotenv,
)
from interviewer_domain.providers.in_memory import InMemoryStorage


class _Auth:
    async def validate(self, token: str) -> str:
        assert token == "firebase-id-token"
        return "firebase-user"


class _STT:
    async def transcribe(self, audio, turn_id, token):
        assert audio and len(audio) > 0
        return TranscriptSegment(turn_id, "candidate", "I led a clear system design project.")


class _LLM:
    async def generate(self, prompt, token):
        assert "technical" in prompt or "recruiter" in prompt
        return "Tell me about the result and tradeoffs."


class _TTS:
    async def synthesize(self, text, token):
        assert text
        return b"\x00\x01" * 32


def _providers():
    return RehearsalProviders(
        _Auth(), _STT(), _LLM(), _TTS(), InMemoryPersistentDataStore(), InMemoryStorage(), DeterministicEvaluator()
    )


class AgentRoleFlowTests(unittest.IsolatedAsyncioTestCase):
    """Exercise the real domain orchestration with provider seams only."""

    async def test_both_agent_journeys_use_fixtures_and_complete_lifecycle(self):
        resume = Path("tests/demo_resume.pdf")
        job = Path("tests/demo_jobdescription.txt")
        self.assertTrue(resume.is_file())
        self.assertTrue(job.is_file())
        for mode in (InterviewMode.RECRUITER, InterviewMode.TECHNICAL):
            providers = _providers()
            interviewer = InterviewerAgent(providers, "firebase-id-token")
            record, turns, evaluation = await interviewer.run(
                mode, resume, job, IntervieweeAgent((b"candidate audio buffer",)), turn_count=2
            )
            self.assertEqual(record.status, "completed")
            self.assertEqual(len(turns), 2)
            self.assertFalse(turns[0].partial.is_final)
            self.assertTrue(turns[0].final.is_final)
            self.assertLess(turns[0].partial.start_ms, turns[0].final.end_ms)
            self.assertGreater(evaluation.score or 0, 0)
            self.assertTrue(providers.data.list_transcripts("firebase-user", record.id))
            await interviewer.delete(record)
            self.assertEqual(providers.data.interviews, {})

    async def test_transcript_writer_preserves_roles_timestamps_and_turns(self):
        providers = _providers()
        interviewer = InterviewerAgent(providers, "firebase-id-token")
        _, turns, _ = await interviewer.run(
            InterviewMode.TECHNICAL,
            Path("tests/demo_resume.pdf"),
            Path("tests/demo_jobdescription.txt"),
            IntervieweeAgent((b"candidate audio buffer",)),
            turn_count=2,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = write_rehearsal_transcript(directory + "/transcript.txt", ((InterviewMode.TECHNICAL, turns),))
            transcript = Path(output).read_text(encoding="utf-8")
        self.assertIn("Interviewee / candidate (final):", transcript)
        self.assertIn("Interviewer / technical:", transcript)
        self.assertIn("00:00.000", transcript)
        self.assertEqual(transcript.count("[turn "), 4)

    def test_dotenv_loader_preserves_existing_environment_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("LLM_API_KEY=hidden\nLLM_MODEL=live-model\n", encoding="utf-8")
            values = load_dotenv(env_file, {"LLM_API_KEY": "already-set"})
        self.assertEqual(values["LLM_API_KEY"], "already-set")
        self.assertEqual(values["LLM_MODEL"], "live-model")



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
