"""Behavior-level Phase 14 full user acceptance tests."""

import asyncio
import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from uuid import uuid4

from interviewer_domain.contracts import (
    CancellationToken,
    ErrorCode,
    ProviderError,
)
from interviewer_domain.e2e_acceptance import (
    FORBIDDEN,
    MARKERS,
    run_local_acceptance_sync,
)
from interviewer_domain.evaluation import (
    InterviewContext,
    PostInterviewEvaluationService,
)
from interviewer_domain.live_voice import (
    LiveVoiceOrchestrator,
    PrefetchGuard,
    PrefetchedResponse,
)
from interviewer_domain.models import InterviewMode, InterviewSession
from interviewer_domain.persistence import (
    InMemoryPersistentDataStore,
    PersistenceService,
    UploadValidator,
)
from interviewer_domain.providers import (
    InMemoryDataStore,
    InMemoryEventBus,
    InMemorySecondaryResponse,
    InMemoryStorage,
    InMemoryStreamingLLM,
    InMemoryStreamingSTT,
    InMemoryStreamingTTS,
)
from interviewer_domain.routing import FallbackRouter
from interviewer_domain.transport import (
    BrowserSessionState,
    LocalWebRTCBoundary,
    SessionEventType,
    SignalingMessage,
    SignalingType,
    TransportValidationError,
)


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
        record = persistence.create_interview(
            "candidate", InterviewMode.TECHNICAL, datetime.now(timezone.utc)
        )
        with self.assertRaises(ProviderError):
            data.get_interview("other-user", record.id)
        with self.assertRaises(ProviderError):
            PostInterviewEvaluationService(data).evaluate(
                "candidate",
                record.id,
                InterviewContext(InterviewMode.TECHNICAL, "Engineer", "senior"),
                (),
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


class ProviderOutageFallbackTests(unittest.TestCase):
    """Verify FallbackRouter skips failing providers and uses the next healthy one."""

    def test_fallback_to_second_provider_on_first_failure(self) -> None:
        """Router tries the second provider when the first raises UNAVAILABLE."""

        class _FailingProvider:
            async def health(self):
                from interviewer_domain.contracts import HealthStatus

                return HealthStatus(False, "down")

            async def transcribe_stream(self, audio, turn_id, token):
                raise ProviderError(ErrorCode.UNAVAILABLE, "provider down")
                yield  # pragma: no cover

        class _HealthyProvider:
            async def health(self):
                from interviewer_domain.contracts import HealthStatus

                return HealthStatus(True)

            async def transcribe_stream(self, audio, turn_id, token):
                from interviewer_domain.models import TranscriptSegment

                yield TranscriptSegment(
                    turn_id, "candidate", "fallback worked", True, 0, 100
                )

        async def _run():
            router = FallbackRouter([_FailingProvider(), _HealthyProvider()], "stt")
            token = CancellationToken()

            async def _call(provider, t):
                result = []
                async for segment in provider.transcribe_stream(b"audio", uuid4(), t):
                    result.append(segment)
                return result

            return await router.run(_call, token)

        segments = asyncio.run(_run())
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].text, "fallback worked")

    def test_all_providers_fail_raises_last_error(self) -> None:
        """Router raises ProviderError when every provider fails."""

        class _AlwaysFail:
            async def health(self):
                from interviewer_domain.contracts import HealthStatus

                return HealthStatus(False)

            async def generate_stream(self, prompt, token):
                raise ProviderError(ErrorCode.UNAVAILABLE, "all down")

        async def _run():
            router = FallbackRouter([_AlwaysFail(), _AlwaysFail()], "llm")
            token = CancellationToken()
            await router.run(lambda p, t: p.generate_stream("hi", t), token)

        with self.assertRaises(ProviderError) as ctx:
            asyncio.run(_run())
        self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

    def test_cancelled_error_skips_fallback(self) -> None:
        """Router re-raises CANCELLED immediately without trying the next provider."""
        call_count = 0

        class _CancelledProvider:
            async def health(self):
                from interviewer_domain.contracts import HealthStatus

                return HealthStatus(True)

            async def generate(self, prompt, token):
                nonlocal call_count
                call_count += 1
                raise ProviderError(ErrorCode.CANCELLED, "cancelled")

        class _SecondProvider:
            async def health(self):
                from interviewer_domain.contracts import HealthStatus

                return HealthStatus(True)

            async def generate(self, prompt, token):
                nonlocal call_count
                call_count += 1
                return "should not reach"

        async def _run():
            router = FallbackRouter([_CancelledProvider(), _SecondProvider()], "llm")
            token = CancellationToken()
            await router.run(lambda p, t: p.generate("hi", t), token)

        with self.assertRaises(ProviderError) as ctx:
            asyncio.run(_run())
        self.assertEqual(ctx.exception.code, ErrorCode.CANCELLED)
        self.assertEqual(call_count, 1)


class MicrophoneDenialTests(unittest.TestCase):
    """Verify the media boundary rejects empty and unauthorized media frames."""

    def test_empty_microphone_frame_rejected(self) -> None:
        """Capture of an empty audio frame raises TransportValidationError."""
        boundary = LocalWebRTCBoundary(uuid4())
        with self.assertRaises(TransportValidationError) as ctx:
            asyncio.run(boundary.capture_microphone(b""))
        self.assertEqual(str(ctx.exception), "media frame is empty")

    def test_signaling_with_media_payload_rejected(self) -> None:
        """Signaling messages containing audio bytes are rejected."""
        with self.assertRaises(TransportValidationError) as ctx:
            SignalingMessage(
                uuid4(), SignalingType.OFFER, {"sdp": "v=0", "audio": b"secret"}, "c1"
            )
        self.assertIn("cannot contain media", str(ctx.exception))

    def test_unconnected_boundary_no_playback(self) -> None:
        """Playback raises when no media frames are buffered."""
        boundary = LocalWebRTCBoundary(uuid4())
        with self.assertRaises(TransportValidationError):
            asyncio.run(boundary.playback())


class CancellationTimeoutTests(unittest.TestCase):
    """Verify cooperative cancellation propagates through providers."""

    def test_cancelled_token_raises_on_use(self) -> None:
        """A pre-cancelled token raises CANCELLED at the next cooperative check."""
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(ProviderError) as ctx:
            token.raise_if_cancelled()
        self.assertEqual(ctx.exception.code, ErrorCode.CANCELLED)

    def test_cancellation_during_streaming_stops_output(self) -> None:
        """Cancelling between streaming chunks yields only already-emitted chunks."""
        provider = InMemoryStreamingLLM("word1 word2 word3 word4")

        async def _run():
            token = CancellationToken()
            chunks = []
            try:
                async for chunk in provider.generate_stream("test", token):
                    chunks.append(chunk)
                    if len(chunks) == 2:
                        token.cancel()
            except ProviderError:
                pass
            return chunks

        chunks = asyncio.run(_run())
        self.assertLessEqual(len(chunks), 3)

    def test_orchestrator_interrupt_sets_interrupted_flag(self) -> None:
        """LiveVoiceOrchestrator.interrupt() sets interrupted on active token."""
        session = InterviewSession("user", InterviewMode.TECHNICAL, uuid4())
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        orchestrator = LiveVoiceOrchestrator(
            session,
            [InMemoryStreamingSTT("test")],
            [InMemoryStreamingLLM("response")],
            [InMemoryStreamingTTS()],
            store,
            events,
            InMemorySecondaryResponse(),
        )
        token = CancellationToken()
        orchestrator._active_token = token
        orchestrator.interrupt()
        self.assertTrue(token._cancelled)


class StaleResponseTests(unittest.TestCase):
    """Verify PrefetchGuard rejects responses whose answer digest has changed."""

    def test_matching_answer_returns_prefetched_text(self) -> None:
        """Same answer text and sequence returns the cached response."""
        from interviewer_domain.live_voice import _digest

        guard = PrefetchGuard()
        answer = "test answer"
        guard.add(PrefetchedResponse(1, _digest(answer), "cached"))
        result = guard.take(answer, 1)
        self.assertIsNotNone(result)
        self.assertEqual(result.text, "cached")

    def test_changed_answer_returns_none(self) -> None:
        """Different answer text returns None and clears the cache."""
        from interviewer_domain.live_voice import _digest

        guard = PrefetchGuard()
        guard.add(PrefetchedResponse(1, _digest("original answer"), "cached"))
        result = guard.take("different answer", 1)
        self.assertIsNone(result)
        self.assertEqual(len(guard._items), 0)

    def test_wrong_sequence_returns_none(self) -> None:
        """Matching digest but wrong turn sequence returns None."""
        from interviewer_domain.live_voice import _digest

        guard = PrefetchGuard()
        answer = "test answer"
        guard.add(PrefetchedResponse(1, _digest(answer), "cached"))
        result = guard.take(answer, 2)
        self.assertIsNone(result)

    def test_bounded_capacity(self) -> None:
        """Only the most recent N items are retained."""
        from interviewer_domain.live_voice import _digest

        guard = PrefetchGuard(maximum=2)
        guard.add(PrefetchedResponse(1, _digest("first answer"), "first"))
        guard.add(PrefetchedResponse(2, _digest("second answer"), "second"))
        guard.add(PrefetchedResponse(3, _digest("third answer"), "third"))
        self.assertEqual(len(guard._items), 2)
        result = guard.take("first answer", 1)
        self.assertIsNone(result)


class ReconnectTests(unittest.TestCase):
    """Verify BrowserSessionState preserves state across disconnect and reconnect."""

    def test_reconnect_returns_events_after_cursor(self) -> None:
        """Reconnect replays only events newer than the acknowledged sequence."""
        state = BrowserSessionState(uuid4(), "owner")
        state.publish(SessionEventType.TRANSCRIPT_FINAL, {"text": "a"}, "c1")
        state.publish(SessionEventType.TRANSCRIPT_FINAL, {"text": "b"}, "c2")
        state.disconnect("owner")
        resumed = state.connect("owner", after_sequence=1)
        self.assertEqual(len(resumed), 1)
        self.assertEqual(resumed[0].payload["text"], "b")

    def test_non_owner_reconnect_rejected(self) -> None:
        """A non-owner identity is rejected on reconnect."""
        state = BrowserSessionState(uuid4(), "owner")
        with self.assertRaises(TransportValidationError) as ctx:
            state.connect("attacker", after_sequence=0)
        self.assertIn("does not match", str(ctx.exception))

    def test_disconnected_state_not_lost(self) -> None:
        """Event history persists after disconnect for later reconnect."""
        state = BrowserSessionState(uuid4(), "owner")
        state.publish(SessionEventType.TRANSCRIPT_FINAL, {"text": "x"}, "c1")
        state.disconnect("owner")
        self.assertFalse(state.connected)
        resumed = state.connect("owner", after_sequence=0)
        self.assertEqual(len(resumed), 1)
        self.assertTrue(state.connected)


if __name__ == "__main__":
    unittest.main()
