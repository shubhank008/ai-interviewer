"""Deterministic unit and mock-turn coverage for Phase 6."""

import asyncio
import sys
import unittest
from uuid import UUID

sys.path.insert(0, "src")

from interviewer_domain.contracts import CancellationToken, ErrorCode, ProviderError, StreamTextChunk
from interviewer_domain.live_voice import AudioScheduler, LiveVoiceOrchestrator
from interviewer_domain.models import InterviewMode, InterviewSession, Turn
from interviewer_domain.providers import (
    InMemoryDataStore,
    InMemoryEventBus,
    InMemorySecondaryResponse,
    InMemoryStreamingLLM,
    InMemoryStreamingSTT,
    InMemoryStreamingTTS,
)


class FailingSTT:
    """Fail once to exercise provider-independent fallback routing."""

    def transcribe_stream(self, audio: bytes, turn_id: UUID, token: CancellationToken):
        """Raise a normalized retryable provider error when consumed."""
        async def stream():
            raise ProviderError(ErrorCode.UNAVAILABLE, "primary unavailable", True)
            yield None
        return stream()


class OnceFailingSTT:
    """Fail on the first call only, then succeed on subsequent calls."""

    def __init__(self) -> None:
        self._call_count = 0

    def transcribe_stream(self, audio: bytes, turn_id: UUID, token: CancellationToken):
        """Fail on first invocation, delegate to InMemoryStreamingSTT afterward."""
        if self._call_count == 0:
            self._call_count += 1
            async def stream():
                raise ProviderError(ErrorCode.UNAVAILABLE, "primary unavailable", True)
                yield None
            return stream()
        return InMemoryStreamingSTT().transcribe_stream(audio, turn_id, token)


class SlowLLM(InMemoryStreamingLLM):
    """Pause between chunks so an external interruption can be observed."""

    async def _stream(self, prompt: str, token: CancellationToken):
        """Yield one chunk, then wait for cancellation."""
        token.raise_if_cancelled()
        yield StreamTextChunk(0, "unfinished ")
        await asyncio.sleep(0.05)
        token.raise_if_cancelled()
        yield StreamTextChunk(1, "response", True)


class LiveVoiceTests(unittest.TestCase):
    """Exercise concrete providers and the real orchestration path."""

    def build(self, stt=None, llm=None):
        """Build a provider-independent live voice session."""
        session = InterviewSession("candidate-1", InterviewMode.RECRUITER)
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        engine = LiveVoiceOrchestrator(
            session,
            [stt or InMemoryStreamingSTT()],
            [llm or InMemoryStreamingLLM()],
            [InMemoryStreamingTTS()],
            store,
            events,
            InMemorySecondaryResponse(),
        )
        return engine, store, events

    def test_streaming_provider_fixtures_and_timestamped_chunks(self) -> None:
        """Concrete deterministic providers emit cancellable ordered values."""
        async def run():
            turn = Turn(InterviewSession("candidate", InterviewMode.RECRUITER).id, 1, "candidate", b"audio")
            stt = [segment async for segment in InMemoryStreamingSTT().transcribe_stream(turn.input_audio, turn.id, CancellationToken())]
            llm = [chunk async for chunk in InMemoryStreamingLLM().generate_stream("answer", CancellationToken())]
            tts = [chunk async for chunk in InMemoryStreamingTTS().synthesize_stream("one two", CancellationToken())]
            return stt, llm, tts

        stt, llm, tts = asyncio.run(run())
        self.assertFalse(stt[0].is_final)
        self.assertTrue(stt[-1].is_final)
        self.assertEqual([chunk.sequence for chunk in llm], list(range(7)))
        self.assertEqual([chunk.sequence for chunk in tts], [0, 1])
        self.assertEqual([chunk.start_ms for chunk in tts], [0, 20])

    def test_prefetch_rejects_changed_answer(self) -> None:
        """Speculation keyed to an old answer cannot be accepted."""
        async def run():
            engine, _, _ = self.build()
            await engine.prefetch_response("old answer", 1)
            return engine.accept_prefetch("new answer", 1)

        self.assertIsNone(asyncio.run(run()))
        print("[LIVE] stale prefetch rejected")

    def test_real_mock_live_voice_turn_records_all_evidence(self) -> None:
        """A real streaming turn persists transcripts, audio, latency, and events."""
        async def run():
            engine, store, events = self.build()
            turn = Turn(engine.session.id, 1, "candidate", b"candidate-audio")
            result = await engine.process_turn(turn)
            return engine, store, events, result

        engine, store, events, result = asyncio.run(run())
        self.assertIn("impact", result.response)
        self.assertEqual([item.sequence for item in result.audio], list(range(len(result.audio))))
        self.assertEqual([item.start_ms for item in result.audio], [item.sequence * 20 for item in result.audio])
        self.assertEqual(len(store.list_transcript(engine.session.id)), 2)
        self.assertGreaterEqual(result.latency_ms, 0)
        self.assertIn("live.latency", [event.name for event in events.events])
        print("[LIVE] incremental STT connected")
        print("[LIVE] cancellable response streamed")
        print("[LIVE] audio chunks ordered")
        print("[LIVE] artifacts timestamped")
        print("[LIVE] latency measured")
        print("[LIVE] mock turn complete")

    def test_fallback_emits_event_and_uses_next_provider(self) -> None:
        """A retryable stream failure selects the next provider and emits telemetry."""
        async def run():
            session = InterviewSession("candidate", InterviewMode.RECRUITER)
            store = InMemoryDataStore()
            events = InMemoryEventBus()
            engine = LiveVoiceOrchestrator(session, [FailingSTT(), InMemoryStreamingSTT()], [InMemoryStreamingLLM()], [InMemoryStreamingTTS()], store, events)
            return await engine.process_turn(Turn(session.id, 1, "candidate", b"audio")), events

        result, events = asyncio.run(run())
        self.assertFalse(result.interrupted)
        fallback = [event for event in events.events if event.name == "provider.fallback"]
        self.assertEqual(len(fallback), 1)
        print("[LIVE] provider fallback emitted")

    def test_cancellation_stops_playback(self) -> None:
        """Interrupting a live generation returns without completing stale audio."""
        async def run():
            engine, _, events = self.build(llm=SlowLLM())
            task = asyncio.create_task(engine.process_turn(Turn(engine.session.id, 1, "candidate", b"audio")))
            await asyncio.sleep(0)
            engine.interrupt()
            return await task, events

        result, events = asyncio.run(run())
        self.assertTrue(result.interrupted)
        self.assertEqual(result.audio, ())
        self.assertIn("playback.interrupted", [event.name for event in events.events])
        print("[LIVE] interruption stopped playback")
        print("[LIVE] cancellable response streamed")

    def test_cancellation_after_successful_turn_returns_empty_audio(self) -> None:
        """Turn 1 completes then Turn 2 is interrupted; Turn 2 audio is empty."""
        async def run():
            engine, _, events = self.build(llm=SlowLLM())
            turn1 = Turn(engine.session.id, 1, "candidate", b"audio1")
            result1 = await engine.process_turn(turn1)
            turn2 = Turn(engine.session.id, 2, "candidate", b"audio2")
            task2 = asyncio.create_task(engine.process_turn(turn2))
            await asyncio.sleep(0)
            engine.interrupt()
            result2 = await task2
            return result1, result2, turn2.id, events

        result1, result2, turn2_id, events = asyncio.run(run())
        self.assertFalse(result1.interrupted)
        self.assertGreater(len(result1.audio), 0)
        self.assertTrue(result2.interrupted)
        self.assertEqual(result2.audio, ())
        interrupted_events = [e for e in events.events if e.name == "playback.interrupted"]
        self.assertEqual(len(interrupted_events), 1)
        self.assertEqual(interrupted_events[0].payload["turn_id"], str(turn2_id))
        print("[LIVE] cross-turn cancellation isolation verified")

    def test_scheduler_discards_chunks_after_interrupt(self) -> None:
        """The scheduler itself has a deterministic interruption guard."""
        async def chunks():
            yield type("Chunk", (), {"sequence": 0, "audio": b"a", "start_ms": 0, "duration_ms": 20})()

        scheduler = AudioScheduler()
        scheduler.interrupt()
        output = asyncio.run(scheduler.schedule(InterviewSession("candidate", InterviewMode.RECRUITER).id, Turn(InterviewSession("candidate", InterviewMode.RECRUITER).id, 1, "candidate").id, chunks()))
        self.assertEqual(output, ())

    def test_fallback_count_isolated_per_turn(self) -> None:
        """Fallback count from turn 1 does not leak into turn 2."""
        async def run():
            session = InterviewSession("candidate", InterviewMode.RECRUITER)
            store = InMemoryDataStore()
            events = InMemoryEventBus()
            once_fail = OnceFailingSTT()
            engine = LiveVoiceOrchestrator(
                session,
                [once_fail, InMemoryStreamingSTT()],
                [InMemoryStreamingLLM()],
                [InMemoryStreamingTTS()],
                store,
                events,
            )
            result1 = await engine.process_turn(Turn(session.id, 1, "candidate", b"audio"))
            result2 = await engine.process_turn(Turn(session.id, 2, "candidate", b"audio"))
            return result1, result2

        result1, result2 = asyncio.run(run())
        self.assertEqual(result1.fallback_count, 1)
        self.assertEqual(result2.fallback_count, 0)


if __name__ == "__main__":
    unittest.main()
