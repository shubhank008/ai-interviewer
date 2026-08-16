"""Offline contract tests for Phase 15 concrete transport boundaries."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from interviewer_domain.contracts import CancellationToken, ErrorCode, ProviderError
from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
from interviewer_domain.evaluation import InterviewContext
from interviewer_domain.models import InterviewMode, TranscriptSegment
from uuid import uuid4
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
        self.assertEqual(skip_reason("openrouter", {}), "required configuration absent: LLM_API_KEY, LLM_MODEL")
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

    def test_openrouter_evaluator_normalizes_structured_feedback(self) -> None:
        class Transport:
            def complete(self, payload: dict, api_key: str) -> dict:
                self.payload = payload
                return {"choices": [{"message": {"content": json.dumps({
                    "score": 82,
                    "dimensions": ["Strong ownership"],
                    "summary": "Clear answer.",
                    "strengths": ["Ownership"],
                    "weaknesses": ["Brevity"],
                    "recommendations": ["Use STAR."],
                })}}]}

        transport = Transport()
        segment = TranscriptSegment(uuid4(), "candidate", "I led the migration and improved reliability.")
        result = OpenRouterEvaluator(transport, "test-key", "fast-model").evaluate(
            InterviewContext(InterviewMode.TECHNICAL, "Engineer", "senior"), (segment,)
        )
        self.assertEqual(result.score, 82)
        self.assertEqual(result.strengths, ("Ownership",))
        self.assertEqual(transport.payload["temperature"], 0)

    def test_openrouter_evaluator_rejects_invalid_score(self) -> None:
        class Transport:
            def complete(self, payload: dict, api_key: str) -> dict:
                return {"choices": [{"message": {"content": '{"score": 101}'}}]}

        segment = TranscriptSegment(uuid4(), "candidate", "An answer.")
        with self.assertRaises(ProviderError) as context:
            OpenRouterEvaluator(Transport(), "test-key", "fast-model").evaluate(
                InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid"), (segment,)
            )
        self.assertEqual(context.exception.code, ErrorCode.INTERNAL)

    def test_openrouter_evaluator_accepts_fenced_and_content_part_json(self) -> None:
        class Transport:
            def __init__(self, content: object) -> None:
                self.content = content
            def complete(self, payload: dict, api_key: str) -> dict:
                return {"choices": [{"message": {"content": self.content}}]}

        value = {"score": 70, "dimensions": [{"dimension": "Communication", "assessment": "Clear"}]}
        fenced = "```json\n" + json.dumps(value) + "\n```"
        parts = [{"type": "text", "text": json.dumps(value)}]
        segment = TranscriptSegment(uuid4(), "candidate", "An answer.")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        self.assertEqual(OpenRouterEvaluator(Transport(fenced), "key", "model").evaluate(context, (segment,)).score, 70)
        self.assertEqual(OpenRouterEvaluator(Transport(parts), "key", "model").evaluate(context, (segment,)).score, 70)


    def test_local_model_constructor_never_downloads_missing_model(self) -> None:
        from interviewer_domain.provider_integration import FasterWhisperLocalBackend

        with self.assertRaises(IntegrationSkipped):
            FasterWhisperLocalBackend("/definitely/not/a/model")


if __name__ == "__main__":
    unittest.main()
