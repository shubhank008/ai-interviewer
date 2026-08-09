"""Phase 11 runtime configuration and provider readiness tests."""

import asyncio
import unittest
from uuid import uuid4

from interviewer_domain.configuration import (
    ConfigurationError,
    ProviderBackends,
    ProviderReadinessChecker,
    RuntimeProfile,
    RuntimeSettings,
    compose_providers,
)
from interviewer_domain.contracts import CancellationToken
from interviewer_domain.models import InterviewMode, InterviewSession, Turn
from interviewer_domain.providers import InMemoryDataStore, InMemoryEventBus
from interviewer_domain.turn import MockTurnRunner


class WhisperFixture:
    """Return deterministic text through the local STT adapter seam."""

    def transcribe(self, audio: bytes) -> str:
        """Transcribe fixture audio."""
        return "I delivered the project."


class SpeechFixture:
    """Return deterministic bytes through the local TTS adapter seam."""

    def synthesize(self, text: str) -> bytes:
        """Synthesize fixture speech bytes."""
        return b"AUDIO:" + text.encode()


class LLMFixture:
    """Return a provider-shaped completion without network access."""

    async def complete(self, payload: dict[str, object], api_key: str) -> dict[str, object]:
        """Complete the injected request."""
        return {"choices": [{"message": {"content": "Tell me about the result."}}]}


class RuntimeConfigurationTests(unittest.TestCase):
    """Exercise public configuration and composition behavior."""

    def test_local_defaults_are_explicit_and_secret_free(self) -> None:
        """Local settings select deterministic providers and safe defaults."""
        settings = RuntimeSettings.from_env({})
        providers = compose_providers(settings)
        self.assertEqual(settings.profile, RuntimeProfile.LOCAL)
        self.assertEqual(settings.retention_days, 14)
        self.assertEqual(settings.diagnostics()["secrets_configured"], {"firebase_api_key": False, "stt_api_key": False, "tts_api_key": False, "llm_api_key": False})
        self.assertEqual([provider.capabilities().name for provider in providers.stt], ["in-memory-stt"])
        print("[PHASE11] config-local-ok")
        print("[PHASE11] diagnostics-redacted")

    def test_production_missing_required_configuration_fails_safely(self) -> None:
        """Production never silently falls back to the local profile."""
        with self.assertRaisesRegex(ConfigurationError, "production configuration is missing"):
            RuntimeSettings.from_env({"APP_PROFILE": "production"})
        diagnostics = str(RuntimeSettings.from_env({}).diagnostics())
        self.assertNotIn("runtime-only-test-key", diagnostics)
        self.assertNotIn("private-key-material", diagnostics)
        print("[PHASE11] config-production-fail-safe")

    def test_production_shaped_adapters_and_health_contract(self) -> None:
        """Injected adapter seams work without optional imports or network access."""
        settings = RuntimeSettings.from_env(
            {
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "demo-project",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "faster-whisper",
                "STT_FALLBACK_PROVIDER": "in-memory",
                "TTS_PROVIDER": "piper",
                "TTS_FALLBACK_PROVIDER": "in-memory",
                "LLM_PROVIDER": "openrouter",
                "LLM_FALLBACK_PROVIDER": "in-memory",
                "LLM_API_KEY": "runtime-only-test-key",
            }
        )
        providers = compose_providers(settings, ProviderBackends(WhisperFixture(), SpeechFixture(), LLMFixture()))
        reports = asyncio.run(ProviderReadinessChecker(providers, required=True).check())
        self.assertTrue(all(report.healthy for report in reports))
        self.assertEqual([report.descriptors[0].name for report in reports], ["faster-whisper", "piper-kokoro", "openrouter"])
        self.assertEqual(asyncio.run(providers.stt[0].transcribe(b"audio", uuid4(), CancellationToken())).text, "I delivered the project.")
        self.assertEqual(asyncio.run(providers.tts[0].synthesize("hello", CancellationToken())), b"AUDIO:hello")
        self.assertIn("result", asyncio.run(providers.llm[0].generate("prompt", CancellationToken())))
        print("[PHASE11] provider-health-capabilities-ok")

    def test_provider_fallback_runs_after_unavailable_primary(self) -> None:
        """A provider-shaped primary failure uses the configured deterministic fallback."""
        settings = RuntimeSettings.from_env(
            {
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "demo-project",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "faster-whisper",
                "STT_FALLBACK_PROVIDER": "in-memory",
                "TTS_PROVIDER": "piper",
                "TTS_FALLBACK_PROVIDER": "in-memory",
                "LLM_PROVIDER": "openrouter",
                "LLM_FALLBACK_PROVIDER": "in-memory",
                "LLM_API_KEY": "runtime-only-test-key",
            }
        )
        providers = compose_providers(settings)
        stt_router, _, _ = providers.routers()

        async def call(provider, token):
            return await provider.transcribe(b"audio", uuid4(), token)

        segment = asyncio.run(stt_router.run(call, CancellationToken()))
        self.assertEqual(segment.text, "I built a reliable service.")
        print("[PHASE11] provider-fallback-e2e-ok")

    def test_local_runtime_executes_real_mock_turn_path(self) -> None:
        """The configured local capabilities produce transcript, response, and audio."""
        providers = compose_providers(RuntimeSettings.from_env({}))
        session = InterviewSession("local-user", InterviewMode.RECRUITER)
        store = InMemoryDataStore()
        events = InMemoryEventBus()
        runner = MockTurnRunner(providers.stt[0], providers.llm[0], providers.tts[0], store, events)
        turn = Turn(session.id, 1, "candidate", b"candidate audio")
        response, audio = asyncio.run(runner.run(turn))
        self.assertEqual(store.transcripts[turn.id][0].text, "I built a reliable service.")
        self.assertTrue(response)
        self.assertTrue(audio.startswith(b"WAV-MOCK:"))
        print("[PHASE11] mock-runtime-e2e-ok")


if __name__ == "__main__":
    unittest.main()
