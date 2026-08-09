"""Executable Phase 9 production hardening evidence."""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from interviewer_api.app import APP_VERSION, app
from interviewer_domain.benchmark import ProviderBenchmark
from interviewer_domain.contracts import CancellationToken, ErrorCode, ProviderError
from interviewer_domain.documents import LocalDocumentParser
from interviewer_domain.evaluation import (
    InterviewContext,
    PostInterviewEvaluationService,
)
from interviewer_domain.live_voice import LiveVoiceOrchestrator
from interviewer_domain.models import InterviewMode, InterviewSession, Turn
from interviewer_domain.persistence import (
    FixedWindowRateLimiter,
    InMemoryPersistentDataStore,
    InterviewRecord,
)
from interviewer_domain.providers import (
    InMemoryDataStore,
    InMemoryEventBus,
    InMemoryLLM,
    InMemoryStreamingLLM,
    InMemoryStreamingSTT,
    InMemoryStreamingTTS,
    InMemorySTT,
    InMemoryTTS,
)
from interviewer_domain.retrieval import (
    DeterministicEmbeddingProvider,
    InMemoryVectorStore,
    TopicRetriever,
)
from interviewer_domain.routing import FallbackRouter
from interviewer_domain.transport import LocalSessionEventChannel, SessionEventType


class Phase9Tests(unittest.TestCase):
    """Exercise public application and domain behavior end to end."""

    def test_api_health_version_and_authorization(self) -> None:
        """Call the real ASGI routes and verify safe ownership boundaries."""

        async def run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                health = await client.get("/api/v1/health")
                version = await client.get("/api/v1/version")
                denied = await client.get("/api/v1/history")
                created = await client.post(
                    "/api/v1/sessions",
                    headers={"Authorization": "Bearer dev-token"},
                    json={"mode": "technical"},
                )
                return health, version, denied, created

        health, version, denied, created = asyncio.run(run())
        self.assertEqual(health.json(), {"status": "ok", "version": APP_VERSION})
        self.assertEqual(version.json()["version"], APP_VERSION)
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(created.status_code, 201)
        print("[PHASE9] api-health-ok")
        print("[PHASE9] api-version-ok")

    def test_complete_mock_interview_pipeline(self) -> None:
        """Exercise ingestion, retrieval, live voice, transport, persistence, and evaluation."""
        parser = LocalDocumentParser()
        chunks = parser.parse(
            b"ROLE:\nPython platform engineer building reliable APIs and distributed systems.",
            "text/plain",
            "job_description",
        )
        retriever = TopicRetriever(
            DeterministicEmbeddingProvider(), InMemoryVectorStore()
        )
        asyncio.run(retriever.index(chunks))
        self.assertTrue(asyncio.run(retriever.retrieve("Python APIs", 1)))
        session = InterviewSession("candidate", InterviewMode.TECHNICAL)
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        voice = LiveVoiceOrchestrator(
            session,
            [InMemoryStreamingSTT()],
            [InMemoryStreamingLLM()],
            [InMemoryStreamingTTS()],
            store,
            events,
        )
        result = asyncio.run(
            voice.process_turn(Turn(session.id, 1, "candidate", b"partial-audio"))
        )
        self.assertTrue(result.response)
        self.assertTrue(any(not item.is_final for item in result.transcript))
        self.assertGreater(len(result.audio), 0)
        self.assertEqual(len(result.audio), len(voice.artifacts))
        record = InterviewRecord(
            "candidate",
            InterviewMode.TECHNICAL,
            session.id,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc) + timedelta(days=14),
            "completed",
        )
        data = InMemoryPersistentDataStore()
        data.save_interview(record)
        evaluation = PostInterviewEvaluationService(data).evaluate(
            "candidate",
            session.id,
            InterviewContext(InterviewMode.TECHNICAL, "Engineer", "senior"),
            tuple(result.transcript),
        )
        self.assertIs(data.get_evaluation("candidate", session.id), evaluation)
        channel = LocalSessionEventChannel(session.id)
        channel.publish(SessionEventType.SESSION_STARTED, {}, "e2e")
        self.assertEqual(
            channel.replay(session.id, 0)[0].event_type,
            SessionEventType.SESSION_STARTED,
        )
        print("[PHASE9] mock-interview-e2e-ok")

    def test_resilience_security_retention_and_benchmarks(self) -> None:
        """Exercise fallback, reconnect, cancellation, partial audio, owner isolation, and limits."""
        router = FallbackRouter(["failed", "healthy"], "llm")

        async def call(provider, token):
            if provider == "failed":
                raise ProviderError(ErrorCode.UNAVAILABLE, "fixture", True)
            return provider

        self.assertEqual(asyncio.run(router.run(call, CancellationToken())), "healthy")
        print("[PHASE9] provider-fallback-ok")
        channel = LocalSessionEventChannel(uuid4())
        channel.publish(SessionEventType.SESSION_STARTED, {}, "reconnect")
        channel.publish(SessionEventType.TRANSCRIPT_FINAL, {"text": "ok"}, "reconnect")
        self.assertEqual(len(channel.replay(channel.session_id, 1)), 1)
        print("[PHASE9] reconnect-ok")
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(ProviderError) as cancelled:
            asyncio.run(InMemorySTT().transcribe(b"audio", uuid4(), token))
        self.assertEqual(cancelled.exception.code, ErrorCode.CANCELLED)
        print("[PHASE9] cancellation-ok")

        async def collect_audio():
            return [
                chunk
                async for chunk in InMemoryStreamingTTS().synthesize_stream(
                    "one two", CancellationToken()
                )
            ]

        audio_chunks = asyncio.run(collect_audio())
        self.assertEqual([chunk.start_ms for chunk in audio_chunks], [0, 20])
        print("[PHASE9] partial-audio-ok")
        data = InMemoryPersistentDataStore()
        now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        owned = InterviewRecord(
            "alice", InterviewMode.RECRUITER, created_at=now
        ).with_retention(14)
        expired = InterviewRecord(
            "alice", InterviewMode.RECRUITER, created_at=now - timedelta(days=15)
        ).with_retention(14)
        data.save_interview(owned)
        data.save_interview(expired)
        with self.assertRaises(ProviderError):
            data.get_interview("bob", owned.id, now)
        self.assertEqual(data.purge_expired(now), [expired.id])
        limiter = FixedWindowRateLimiter(1, 60)
        self.assertTrue(limiter.allow("alice", now))
        self.assertFalse(limiter.allow("alice", now))
        print("[PHASE9] authorization-retention-rate-limit-ok")
        report = asyncio.run(
            ProviderBenchmark().run(
                "offline",
                InMemorySTT(),
                InMemoryLLM(),
                InMemoryTTS(),
                [Turn(uuid4(), 1, "candidate", b"audio")],
            )
        )
        self.assertTrue(report.measurements[0].success)
        self.assertEqual(
            asyncio.run(InMemoryTTS().synthesize("secret-free", CancellationToken())),
            b"WAV-MOCK:secret-free",
        )
        print("[PHASE9] benchmark-security-ok")


if __name__ == "__main__":
    unittest.main()
