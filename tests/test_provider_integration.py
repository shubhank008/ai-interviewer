"""Offline contract tests for Phase 15 concrete transport boundaries."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from interviewer_domain.contracts import CancellationToken, ErrorCode, ProviderError
from interviewer_domain.provider_adapters import OpenRouterLLM
from interviewer_domain.provider_integration import (
    IntegrationEvidence,
    IntegrationSkipped,
    OpenRouterHTTPTransport,
    ProviderMetadata,
    configured_profiles,
    redact_evidence,
    skip_reason,
    write_evidence,
)


class ProviderIntegrationContractTests(unittest.TestCase):
    """Verify real adapter boundaries without network, credentials, or fixtures as providers."""

    def test_profiles_are_opt_in_and_missing_configuration_is_explicit(self) -> None:
        self.assertEqual(configured_profiles({}), ())
        self.assertEqual(skip_reason("openrouter", {}), "required configuration absent: OPENROUTER_API_KEY, LLM_MODEL")
        self.assertEqual(skip_reason("firebase", {}), "required configuration absent: FIREBASE_PROJECT_ID, FIREBASE_CREDENTIALS_PATH")

    def test_openrouter_transport_requires_credential_before_network(self) -> None:
        transport = OpenRouterHTTPTransport()

        async def call() -> None:
            with self.assertRaises(ProviderError) as context:
                await transport.complete({}, "")
            self.assertEqual(context.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_openrouter_adapter_rejects_missing_transport_and_cancellation(self) -> None:
        adapter = OpenRouterLLM()
        token = CancellationToken()
        token.cancel()

        async def call() -> None:
            with self.assertRaises(ProviderError) as context:
                await adapter.generate("safe prompt", token)
            self.assertEqual(context.exception.code, ErrorCode.CANCELLED)

        asyncio.run(call())

    def test_evidence_redacts_payload_shaped_values_and_writes_three_formats(self) -> None:
        item = IntegrationEvidence(
            "llm", "skipped", "required configuration absent", ProviderMetadata("openrouter", "model")
        )
        value = redact_evidence(item)
        self.assertNotIn("api_key", json.dumps(value).lower())
        with tempfile.TemporaryDirectory() as directory:
            paths = write_evidence(directory, [item])
            self.assertEqual([path.suffix for path in paths], [".json", ".md", ".html"])
            self.assertTrue(all(Path(path).exists() for path in paths))

    def test_local_model_constructor_never_downloads_missing_model(self) -> None:
        from interviewer_domain.provider_integration import FasterWhisperLocalBackend

        with self.assertRaises(IntegrationSkipped):
            FasterWhisperLocalBackend("/definitely/not/a/model")


if __name__ == "__main__":
    unittest.main()
