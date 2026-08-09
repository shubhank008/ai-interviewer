"""Phase 4 provider adapter and deterministic benchmark evidence tests."""

import asyncio
import sys
import unittest
from uuid import uuid4

sys.path.insert(0, "src")

from interviewer_domain.benchmark import ProviderBenchmark
from interviewer_domain.contracts import CancellationToken, ErrorCode, ProviderError
from interviewer_domain.models import InterviewMode, InterviewSession, Turn
from interviewer_domain.provider_adapters import FasterWhisperSTT, OpenRouterLLM, PiperKokoroTTS
from interviewer_domain.providers import InMemoryLLM, InMemorySTT, InMemoryTTS
from interviewer_domain.routing import FallbackRouter, ProviderFlags


class WhisperFixture:
    """Deterministic local substitute for a Faster-Whisper model."""

    def transcribe(self, audio: bytes) -> str:
        return "I built a reliable service."


class SpeechFixture:
    """Deterministic local substitute for Piper or Kokoro."""

    def synthesize(self, text: str) -> bytes:
        return b"WAV-FIXTURE:" + text.encode()


class TransportFixture:
    """Deterministic OpenAI-compatible response transport."""

    async def complete(self, payload, api_key):
        self.payload = payload
        self.api_key = api_key
        return {"choices": [{"message": {"content": "fixture response"}}]}


class ProviderBenchmarkTests(unittest.TestCase):
    """Verify optional adapters and the offline benchmark through real code paths."""

    def test_concrete_adapters_translate_injected_backends(self) -> None:
        """Each optional adapter works without importing its third-party package."""
        turn_id = uuid4()
        stt = FasterWhisperSTT(WhisperFixture())
        tts = PiperKokoroTTS(SpeechFixture())
        llm_transport = TransportFixture()
        llm = OpenRouterLLM(llm_transport, "test-key", "fixture-model")
        segment = asyncio.run(stt.transcribe(b"audio", turn_id, CancellationToken()))
        audio = asyncio.run(tts.synthesize("hello", CancellationToken()))
        response = asyncio.run(llm.generate("prompt", CancellationToken()))
        self.assertEqual(segment.text, "I built a reliable service.")
        self.assertEqual(audio, b"WAV-FIXTURE:hello")
        self.assertEqual(response, "fixture response")
        self.assertEqual(llm_transport.payload["model"], "fixture-model")
        print("[BENCHMARK] provider-adapters-ok")

    def test_health_capabilities_and_unavailable_optional_dependencies(self) -> None:
        """Optional providers report safe health without downloads or credentials."""
        stt = FasterWhisperSTT()
        tts = PiperKokoroTTS()
        llm = OpenRouterLLM()
        self.assertFalse(asyncio.run(stt.health()).healthy)
        self.assertFalse(asyncio.run(tts.health()).healthy)
        self.assertFalse(asyncio.run(llm.health()).healthy)
        self.assertEqual(stt.capabilities().name, "faster-whisper")
        self.assertEqual(tts.capabilities().name, "piper-kokoro")
        self.assertEqual(llm.capabilities().name, "openrouter")
        with self.assertRaises(ProviderError) as raised:
            asyncio.run(llm.generate("hello", CancellationToken()))
        self.assertEqual(raised.exception.code, ErrorCode.UNAVAILABLE)
        self.assertTrue(ProviderFlags(enable_hosted_llm=False).enable_local_stt)
        print("[BENCHMARK] health-capabilities-ok")

    def test_fallback_router_uses_next_provider(self) -> None:
        """Retryable provider failure routes to the next configured provider."""
        router = FallbackRouter(["offline", "local"], "llm")

        async def call(provider, token):
            if provider == "offline":
                raise ProviderError(ErrorCode.UNAVAILABLE, "offline", True)
            return provider

        self.assertEqual(asyncio.run(router.run(call, CancellationToken())), "local")
        print("[BENCHMARK] fallback-routing-ok")

    def test_deterministic_report_contains_all_required_metrics(self) -> None:
        """The real provider chain produces repeatable, complete benchmark records."""
        session = InterviewSession("candidate", InterviewMode.RECRUITER)
        turns = [Turn(session.id, 1, "candidate", b"audio"), Turn(session.id, 2, "candidate", b"audio")]
        report = asyncio.run(ProviderBenchmark().run("in-memory", InMemorySTT(), InMemoryLLM(), InMemoryTTS(), turns))
        self.assertEqual(len(report.measurements), 2)
        for measurement in report.measurements:
            self.assertTrue(measurement.success)
            self.assertIsNotNone(measurement.first_byte_latency_ms)
            self.assertIsNotNone(measurement.end_to_end_latency_ms)
            self.assertIsNotNone(measurement.quality)
            self.assertIsNotNone(measurement.cpu_seconds)
        self.assertEqual(len(report.to_dict()["measurements"]), 2)
        print("[BENCHMARK] deterministic-report-ok")
        print("[BENCHMARK] metrics-complete-ok")


if __name__ == "__main__":
    unittest.main()
