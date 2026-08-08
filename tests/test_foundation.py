"""Unit and deterministic mock-turn coverage for feature 001."""

import asyncio
import sys
import unittest
from uuid import uuid4

sys.path.insert(0, "src")

from interviewer_domain.contracts import CancellationToken, ErrorCode, ProviderError
from interviewer_domain.models import Evaluation, InterviewMode, InterviewSession, Turn
from interviewer_domain.providers import InMemoryDataStore, InMemoryEventBus, InMemoryLLM, InMemorySTT, InMemoryTTS
from interviewer_domain.turn import MockTurnRunner


class FoundationTests(unittest.TestCase):
    """Verify the normalized foundation through real implementations."""

    def test_domain_models_validate(self) -> None:
        """Models enforce core invariants and retain voice input."""
        session = InterviewSession("candidate-1", InterviewMode.RECRUITER)
        turn = Turn(session.id, 1, "candidate", b"candidate-audio")
        self.assertEqual(turn.input_audio, b"candidate-audio")
        self.assertEqual(Evaluation(session.id, "v1", 100).score, 100)
        with self.assertRaises(ValueError):
            Turn(session.id, 0, "candidate")
        print("[FOUNDATION] domain-models-ok")

    def test_capabilities_and_normalized_cancellation(self) -> None:
        """Providers expose discovery and cancellation uses one error shape."""
        self.assertTrue(asyncio.run(InMemorySTT().health()).healthy)
        self.assertTrue(InMemoryLLM().capabilities().cancellation)
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(ProviderError) as raised:
            token.raise_if_cancelled()
        self.assertEqual(raised.exception.code, ErrorCode.CANCELLED)
        print("[FOUNDATION] capabilities-ok")

    def test_mock_turn_and_lifecycle(self) -> None:
        """The real provider-independent path emits state and audio evidence."""
        session = InterviewSession("candidate-1", InterviewMode.TECHNICAL)
        turn = Turn(session.id, 1, "candidate", b"audio")
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        runner = MockTurnRunner(InMemorySTT(), InMemoryLLM(), InMemoryTTS(), store, events)
        response, audio = asyncio.run(runner.run(turn))
        self.assertIn("impact", response)
        self.assertTrue(audio.startswith(b"WAV-MOCK:"))
        self.assertEqual([event.name for event in events.events], ["turn.started", "turn.processing", "turn.completed"])
        self.assertEqual(len(store.transcripts[turn.id]), 1)
        self.assertIn(session.id, store.recordings)
        print("[FOUNDATION] mock-turn-ok")
        print("[FOUNDATION] lifecycle-ok")

    def test_cancellation_emits_failed_lifecycle(self) -> None:
        """A cancelled turn returns the normalized error and failure event."""
        session = InterviewSession("candidate-1", InterviewMode.RECRUITER)
        events = InMemoryEventBus()
        runner = MockTurnRunner(InMemorySTT(), InMemoryLLM(), InMemoryTTS(), InMemoryDataStore(), events)
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(ProviderError) as raised:
            asyncio.run(runner.run(Turn(session.id, 1, "candidate", b"audio"), token))
        self.assertEqual(raised.exception.code, ErrorCode.CANCELLED)
        self.assertEqual(events.events[-1].name, "turn.failed")


if __name__ == "__main__":
    unittest.main()
