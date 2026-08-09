"""Behavior-driven and deterministic coverage for feature 002."""

import asyncio
import sys
import unittest

sys.path.insert(0, "src")

from interviewer_domain.contracts import CancellationToken, ErrorCode, ProviderError
from interviewer_domain.models import InterviewMode, InterviewSession, SessionStatus, Turn
from interviewer_domain.providers import InMemoryDataStore, InMemoryEventBus, InMemoryLLM, InMemorySTT, InMemoryTTS
from interviewer_domain.session import InterviewSessionEngine, QuestionPlanner, SessionStateError


class SessionEngineTests(unittest.TestCase):
    """Exercise the real provider-independent session state machine."""

    def build(self, mode: InterviewMode = InterviewMode.RECRUITER, stt=None) -> tuple[InterviewSessionEngine, InMemoryDataStore, InMemoryEventBus]:
        """Build an engine with deterministic Phase 1 providers."""
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        engine = InterviewSessionEngine(
            InterviewSession("candidate-1", mode),
            stt or InMemorySTT(),
            InMemoryLLM(),
            InMemoryTTS(),
            store,
            events,
        )
        return engine, store, events

    def test_recruiter_mode_starts_with_recruiter_plan(self) -> None:
        """Recruiter mode asks about background and motivation first."""
        engine, _, _ = self.build()
        plan = asyncio.run(engine.start())
        self.assertEqual(plan.topic, "motivation")
        self.assertEqual(engine.session.status, SessionStatus.ACTIVE.value)
        print("[ENGINE] recruiter-mode-ok")

    def test_technical_mode_starts_with_technical_plan(self) -> None:
        """Technical mode asks about technical depth first."""
        engine, _, _ = self.build(InterviewMode.TECHNICAL)
        plan = asyncio.run(engine.start())
        self.assertEqual(plan.topic, "technical-depth")
        self.assertIn("technically", plan.prompt)
        print("[ENGINE] technical-mode-ok")

    def test_turn_sequence_and_lifecycle_are_ordered_and_correlated(self) -> None:
        """A real turn advances once and emits monotonic correlated events."""
        engine, store, events = self.build()
        asyncio.run(engine.start())
        response, audio = asyncio.run(engine.process_turn(Turn(engine.session.id, 1, "candidate", b"audio")))
        asyncio.run(engine.complete())
        self.assertTrue(len(events.events) >= 5)
        sequences = [event.sequence for event in events.events]
        self.assertEqual(sequences, list(range(1, len(events.events) + 1)))
        correlation_ids = {event.correlation_id for event in events.events}
        self.assertTrue(len(correlation_ids) >= 1)
        turn_events = [e for e in events.events if e.name.startswith("turn.")]
        for event in turn_events:
            self.assertIn("turn_id", event.payload)
        self.assertEqual(len(store.list_transcript(engine.session.id)), 1)
        self.assertTrue(audio.startswith(b"WAV-MOCK:"))
        self.assertIn("impact", response)
        with self.assertRaises(SessionStateError):
            asyncio.run(engine.process_turn(Turn(engine.session.id, 1, "candidate", b"duplicate")))
        print("[ENGINE] lifecycle-ok")
        print("[ENGINE] mock-session-ok")

    def test_changed_answer_invalidates_stale_plan(self) -> None:
        """A plan prepared for one answer cannot be reused for another."""
        engine, _, _ = self.build(InterviewMode.TECHNICAL)
        asyncio.run(engine.start())
        asyncio.run(engine.process_turn(Turn(engine.session.id, 1, "candidate", b"audio")))
        current = engine.question_plan
        self.assertIsNotNone(current)
        self.assertTrue(engine.is_plan_current("I built a reliable service."))
        self.assertFalse(engine.planner.is_current(current, "I changed direction to compensation.", 1))
        self.assertEqual(current.topic, "technical-depth")
        print("[ENGINE] guarded-planning-ok")

    def test_cancellation_is_terminal_without_completion(self) -> None:
        """Cancellation transitions explicitly and never reports completion."""
        engine, _, events = self.build()
        asyncio.run(engine.start())
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(ProviderError) as raised:
            asyncio.run(engine.process_turn(Turn(engine.session.id, 1, "candidate", b"audio"), token))
        self.assertEqual(raised.exception.code, ErrorCode.CANCELLED)
        self.assertEqual(engine.session.status, SessionStatus.CANCELLED.value)
        self.assertNotIn("session.completed", [event.name for event in events.events])
        print("[ENGINE] cancellation-failure-ok")

    def test_provider_failure_is_terminal(self) -> None:
        """Invalid deterministic input transitions the session to failed."""
        engine, _, events = self.build(stt=InMemorySTT())
        asyncio.run(engine.start())
        with self.assertRaises(ProviderError):
            asyncio.run(engine.process_turn(Turn(engine.session.id, 1, "candidate", b"")))
        self.assertEqual(engine.session.status, SessionStatus.FAILED.value)
        self.assertEqual(events.events[-1].name, "session.failed")
        print("[ENGINE] cancellation-failure-ok")

    def test_planner_rejects_empty_follow_up_context(self) -> None:
        """Follow-up preparation requires substantive current context."""
        planner = QuestionPlanner()
        session = InterviewSession("candidate-1", InterviewMode.RECRUITER)
        with self.assertRaises(SessionStateError):
            planner.follow_up(session, " ", 1)


if __name__ == "__main__":
    unittest.main()
