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

    def test_list_transcript_filters_by_session(self) -> None:
        """list_transcript returns only segments belonging to the requested session."""
        session_a = InterviewSession("user-a", InterviewMode.RECRUITER)
        session_b = InterviewSession("user-b", InterviewMode.TECHNICAL)
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        runner = MockTurnRunner(InMemorySTT(), InMemoryLLM(), InMemoryTTS(), store, events)
        turn_a = Turn(session_a.id, 1, "candidate", b"audio-a")
        turn_b = Turn(session_b.id, 1, "candidate", b"audio-b")
        asyncio.run(runner.run(turn_a))
        asyncio.run(runner.run(turn_b))
        segments_a = store.list_transcript(session_a.id)
        segments_b = store.list_transcript(session_b.id)
        self.assertEqual(len(segments_a), 1)
        self.assertEqual(len(segments_b), 1)
        self.assertNotEqual(segments_a[0].turn_id, segments_b[0].turn_id)

    def test_multi_turn_session_lifecycle_sequences(self) -> None:
        """Multiple turns in the same session emit monotonically increasing sequences."""
        session = InterviewSession("candidate-1", InterviewMode.TECHNICAL)
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        runner = MockTurnRunner(InMemorySTT(), InMemoryLLM(), InMemoryTTS(), store, events)
        turn_1 = Turn(session.id, 1, "candidate", b"audio-1")
        turn_2 = Turn(session.id, 2, "candidate", b"audio-2")
        asyncio.run(runner.run(turn_1))
        asyncio.run(runner.run(turn_2))
        sequences = [event.sequence for event in events.events]
        self.assertEqual(sequences, [1, 2, 3, 4, 5, 6])

    def test_multi_session_lifecycle_sequences(self) -> None:
        """Turns in different sessions maintain independent sequence counters."""
        session_a = InterviewSession("user-a", InterviewMode.RECRUITER)
        session_b = InterviewSession("user-b", InterviewMode.TECHNICAL)
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        runner = MockTurnRunner(InMemorySTT(), InMemoryLLM(), InMemoryTTS(), store, events)
        turn_a = Turn(session_a.id, 1, "candidate", b"audio-a")
        turn_b = Turn(session_b.id, 1, "candidate", b"audio-b")
        asyncio.run(runner.run(turn_a))
        asyncio.run(runner.run(turn_b))
        events_a = [e for e in events.events if e.session_id == session_a.id]
        events_b = [e for e in events.events if e.session_id == session_b.id]
        self.assertEqual([e.sequence for e in events_a], [1, 2, 3])
        self.assertEqual([e.sequence for e in events_b], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
