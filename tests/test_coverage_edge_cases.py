"""Edge-case behavioral tests for low-coverage provider adapters and configuration paths.

These tests exercise error handling, boundary conditions, and edge-case branches
in voice adapters, integration transports, configuration validation, and persistence
services using injected fixtures and mocked third-party dependencies.
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from interviewer_domain.contracts import (
    CancellationToken,
    ErrorCode,
    ProviderError,
)
from interviewer_domain.models import Evaluation, InterviewMode, TranscriptSegment


class VoiceAdapterEdgeCases(unittest.TestCase):
    """Behavioral edge cases for FasterWhisperSTT, PiperKokoroTTS, and OpenRouterLLM."""

    def test_stt_transcribe_empty_audio_raises_invalid_request(self) -> None:
        from interviewer_domain.provider_adapters import FasterWhisperSTT

        stt = FasterWhisperSTT()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await stt.transcribe(b"", uuid4(), CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_stt_transcribe_none_backend_raises_unavailable(self) -> None:
        from interviewer_domain.provider_adapters import FasterWhisperSTT

        stt = FasterWhisperSTT(backend=None)

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await stt.transcribe(b"audio", uuid4(), CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)
            self.assertTrue(ctx.exception.retryable)

        asyncio.run(call())

    def test_stt_transcribe_backend_exception_raises_internal(self) -> None:
        from interviewer_domain.provider_adapters import FasterWhisperSTT

        class FailingBackend:
            def transcribe(self, audio: bytes) -> str:
                raise RuntimeError("model crashed")

        stt = FasterWhisperSTT(FailingBackend())

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await stt.transcribe(b"audio", uuid4(), CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)
            self.assertTrue(ctx.exception.retryable)

        asyncio.run(call())

    def test_stt_transcribe_empty_text_raises_internal(self) -> None:
        from interviewer_domain.provider_adapters import FasterWhisperSTT

        class EmptyTextBackend:
            def transcribe(self, audio: bytes) -> str:
                return "   "

        stt = FasterWhisperSTT(EmptyTextBackend())

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await stt.transcribe(b"audio", uuid4(), CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

        asyncio.run(call())

    def test_tts_synthesize_empty_text_raises_invalid_request(self) -> None:
        from interviewer_domain.provider_adapters import PiperKokoroTTS

        tts = PiperKokoroTTS()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await tts.synthesize("", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_tts_synthesize_whitespace_text_raises_invalid_request(self) -> None:
        from interviewer_domain.provider_adapters import PiperKokoroTTS

        tts = PiperKokoroTTS()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await tts.synthesize("   \n  \t  ", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_tts_synthesize_none_backend_raises_unavailable(self) -> None:
        from interviewer_domain.provider_adapters import PiperKokoroTTS

        tts = PiperKokoroTTS(backend=None)

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await tts.synthesize("hello", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)
            self.assertTrue(ctx.exception.retryable)

        asyncio.run(call())

    def test_tts_synthesize_backend_exception_raises_internal(self) -> None:
        from interviewer_domain.provider_adapters import PiperKokoroTTS

        class FailingBackend:
            def synthesize(self, text: str) -> bytes:
                raise OSError("audio device busy")

        tts = PiperKokoroTTS(FailingBackend())

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await tts.synthesize("hello", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)
            self.assertTrue(ctx.exception.retryable)

        asyncio.run(call())

    def test_tts_synthesize_empty_audio_raises_internal(self) -> None:
        from interviewer_domain.provider_adapters import PiperKokoroTTS

        class EmptyAudioBackend:
            def synthesize(self, text: str) -> bytes:
                return b""

        tts = PiperKokoroTTS(EmptyAudioBackend())

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await tts.synthesize("hello", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

        asyncio.run(call())

    def test_llm_generate_empty_prompt_raises_invalid_request(self) -> None:
        from interviewer_domain.provider_adapters import OpenRouterLLM

        llm = OpenRouterLLM()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await llm.generate("", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_llm_generate_no_transport_raises_unavailable(self) -> None:
        from interviewer_domain.provider_adapters import OpenRouterLLM

        llm = OpenRouterLLM(transport=None, api_key="key")

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await llm.generate("prompt", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)
            self.assertTrue(ctx.exception.retryable)

        asyncio.run(call())

    def test_llm_generate_no_api_key_raises_unavailable(self) -> None:
        from interviewer_domain.provider_adapters import OpenRouterLLM

        class FakeTransport:
            async def complete(self, payload, api_key):
                return {}

        llm = OpenRouterLLM(transport=FakeTransport(), api_key=None)

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await llm.generate("prompt", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

        asyncio.run(call())

    def test_llm_generate_malformed_response_raises_internal(self) -> None:
        from interviewer_domain.provider_adapters import OpenRouterLLM

        class MalformedTransport:
            async def complete(self, payload, api_key):
                return {"unexpected": "format"}

        llm = OpenRouterLLM(MalformedTransport(), "key", "model")

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await llm.generate("prompt", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

        asyncio.run(call())

    def test_llm_generate_transport_exception_raises_unavailable(self) -> None:
        from interviewer_domain.provider_adapters import OpenRouterLLM

        class ErrorTransport:
            async def complete(self, payload, api_key):
                raise ConnectionError("network down")

        llm = OpenRouterLLM(ErrorTransport(), "key", "model")

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await llm.generate("prompt", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)
            self.assertTrue(ctx.exception.retryable)

        asyncio.run(call())

    def test_llm_generate_empty_text_raises_internal(self) -> None:
        from interviewer_domain.provider_adapters import OpenRouterLLM

        class EmptyTransport:
            async def complete(self, payload, api_key):
                return {"choices": [{"message": {"content": "   "}}]}

        llm = OpenRouterLLM(EmptyTransport(), "key", "model")

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await llm.generate("prompt", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

        asyncio.run(call())

    def test_stt_cancelled_token_raises_cancelled(self) -> None:
        from interviewer_domain.provider_adapters import FasterWhisperSTT

        token = CancellationToken()
        token.cancel()
        stt = FasterWhisperSTT()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await stt.transcribe(b"audio", uuid4(), token)
            self.assertEqual(ctx.exception.code, ErrorCode.CANCELLED)

        asyncio.run(call())

    def test_tts_cancelled_token_raises_cancelled(self) -> None:
        from interviewer_domain.provider_adapters import PiperKokoroTTS

        token = CancellationToken()
        token.cancel()
        tts = PiperKokoroTTS()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await tts.synthesize("hello", token)
            self.assertEqual(ctx.exception.code, ErrorCode.CANCELLED)

        asyncio.run(call())


class SyncTransportEdgeCases(unittest.TestCase):
    """Behavioral tests for SyncOpenRouterHTTPTransport with mocked httpx."""

    def test_sync_transport_empty_api_key_raises_invalid_request(self) -> None:
        from interviewer_domain.adapters.integrations import SyncOpenRouterHTTPTransport

        transport = SyncOpenRouterHTTPTransport()
        with self.assertRaises(ProviderError) as ctx:
            transport.complete({}, "")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_sync_transport_successful_response(self) -> None:
        from interviewer_domain.adapters.integrations import SyncOpenRouterHTTPTransport

        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        transport = SyncOpenRouterHTTPTransport(timeout=5.0)
        with patch("httpx.Client", return_value=mock_client):
            result = transport.complete({"model": "m"}, "test-key")
        self.assertEqual(result, {"choices": [{"message": {"content": "hi"}}]})

    def test_sync_transport_timeout_raises_provider_error(self) -> None:
        from interviewer_domain.adapters.integrations import SyncOpenRouterHTTPTransport

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        transport = SyncOpenRouterHTTPTransport()
        with patch("httpx.Client", return_value=mock_client):
            with self.assertRaises(ProviderError) as ctx:
                transport.complete({"model": "m"}, "test-key")
            self.assertEqual(ctx.exception.code, ErrorCode.TIMEOUT)
            self.assertTrue(ctx.exception.retryable)

    def test_sync_transport_generic_error_raises_unavailable(self) -> None:
        from interviewer_domain.adapters.integrations import SyncOpenRouterHTTPTransport

        mock_client = MagicMock()
        mock_client.post.side_effect = ConnectionError("network down")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        transport = SyncOpenRouterHTTPTransport()
        with patch("httpx.Client", return_value=mock_client):
            with self.assertRaises(ProviderError) as ctx:
                transport.complete({"model": "m"}, "test-key")
            self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)
            self.assertTrue(ctx.exception.retryable)

    def test_sync_transport_malformed_response_raises_internal(self) -> None:
        from interviewer_domain.adapters.integrations import SyncOpenRouterHTTPTransport

        mock_response = MagicMock()
        mock_response.json.return_value = "not a dict"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        transport = SyncOpenRouterHTTPTransport()
        with patch("httpx.Client", return_value=mock_client):
            with self.assertRaises(ProviderError) as ctx:
                transport.complete({"model": "m"}, "test-key")
            self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)


class IntegrationConstructorEdgeCases(unittest.TestCase):
    """Behavioral tests for integration constructor error paths."""

    def test_piper_missing_path_raises_skipped(self) -> None:
        from interviewer_domain.adapters.integrations import (
            IntegrationSkipped,
            PiperCommandBackend,
        )

        with self.assertRaises(IntegrationSkipped):
            PiperCommandBackend("piper", "/nonexistent/model.onnx")

    def test_piper_empty_command_raises_skipped(self) -> None:
        from interviewer_domain.adapters.integrations import (
            IntegrationSkipped,
            PiperCommandBackend,
        )

        with tempfile.NamedTemporaryFile(suffix=".onnx") as tmp:
            with self.assertRaises(IntegrationSkipped):
                PiperCommandBackend("", tmp.name)

    def test_piper_metadata_returns_valid_metadata(self) -> None:
        from interviewer_domain.adapters.integrations import PiperCommandBackend

        with tempfile.NamedTemporaryFile(suffix=".onnx") as tmp:
            backend = PiperCommandBackend("piper", tmp.name, 16000)
            md = backend.metadata()
            self.assertEqual(md.provider, "piper-kokoro")
            self.assertEqual(md.device, "cpu")
            self.assertIn("16000Hz", md.limitation)

    def test_piper_synthesize_empty_text_raises_invalid_request(self) -> None:
        from interviewer_domain.adapters.integrations import ProviderError

        with tempfile.NamedTemporaryFile(suffix=".onnx") as tmp:
            from interviewer_domain.adapters.integrations import PiperCommandBackend

            backend = PiperCommandBackend("piper", tmp.name)
            with self.assertRaises(ProviderError) as ctx:
                backend.synthesize("   ")
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_piper_synthesize_command_not_found_raises_unavailable(self) -> None:
        from interviewer_domain.adapters.integrations import ProviderError

        with tempfile.NamedTemporaryFile(suffix=".onnx") as tmp:
            from interviewer_domain.adapters.integrations import PiperCommandBackend

            backend = PiperCommandBackend("/nonexistent/piper", tmp.name)
            with self.assertRaises(ProviderError) as ctx:
                backend.synthesize("hello world")
            self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)
            self.assertTrue(ctx.exception.retryable)

    def test_piper_synthesize_timeout_raises_provider_error(self) -> None:
        from interviewer_domain.adapters.integrations import ProviderError

        with tempfile.NamedTemporaryFile(suffix=".onnx") as tmp:
            from interviewer_domain.adapters.integrations import PiperCommandBackend

            backend = PiperCommandBackend("piper", tmp.name)

            def fake_run(*args, **kwargs):
                raise subprocess.TimeoutExpired(cmd="piper", timeout=30)

            with patch("subprocess.run", side_effect=fake_run):
                with self.assertRaises(ProviderError) as ctx:
                    backend.synthesize("hello world")
                self.assertEqual(ctx.exception.code, ErrorCode.TIMEOUT)
                self.assertTrue(ctx.exception.retryable)

    def test_piper_synthesize_empty_output_raises_internal(self) -> None:
        from interviewer_domain.adapters.integrations import ProviderError

        with tempfile.NamedTemporaryFile(suffix=".onnx") as tmp:
            from interviewer_domain.adapters.integrations import PiperCommandBackend

            backend = PiperCommandBackend("piper", tmp.name)

            mock_result = MagicMock()
            mock_result.stdout = b""

            with patch("subprocess.run", return_value=mock_result):
                with self.assertRaises(ProviderError) as ctx:
                    backend.synthesize("hello world")
                self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

    def test_faster_whisper_missing_import_raises_skipped(self) -> None:
        from interviewer_domain.adapters.integrations import (
            IntegrationSkipped,
            FasterWhisperLocalBackend,
        )

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(IntegrationSkipped):
                FasterWhisperLocalBackend(td)

    def test_faster_whisper_metadata_with_mocked_backend(self) -> None:
        from interviewer_domain.adapters.integrations import FasterWhisperLocalBackend

        with tempfile.TemporaryDirectory() as td:
            mock_whisper = MagicMock()
            mock_model = MagicMock()
            mock_whisper.WhisperModel.return_value = mock_model

            with patch.dict(sys.modules, {"faster_whisper": mock_whisper}):
                backend = FasterWhisperLocalBackend(td, device="gpu")
                md = backend.metadata()
                self.assertEqual(md.provider, "faster-whisper")
                self.assertEqual(md.device, "gpu")

    def test_faster_whisper_transcribe_with_mocked_model(self) -> None:
        from interviewer_domain.adapters.integrations import FasterWhisperLocalBackend

        with tempfile.TemporaryDirectory() as td:
            mock_whisper = MagicMock()
            mock_model = MagicMock()
            segment = MagicMock()
            segment.text = "hello world"
            mock_model.transcribe.return_value = ([segment], {})
            mock_whisper.WhisperModel.return_value = mock_model

            with patch.dict(sys.modules, {"faster_whisper": mock_whisper}):
                backend = FasterWhisperLocalBackend(td)
                result = backend.transcribe(b"fake-audio")
                self.assertEqual(result, "hello world")

    def test_faster_whisper_transcribe_empty_audio_raises(self) -> None:
        from interviewer_domain.adapters.integrations import (
            FasterWhisperLocalBackend,
            ProviderError,
        )

        with tempfile.TemporaryDirectory() as td:
            mock_whisper = MagicMock()
            mock_model = MagicMock()
            mock_whisper.WhisperModel.return_value = mock_model

            with patch.dict(sys.modules, {"faster_whisper": mock_whisper}):
                backend = FasterWhisperLocalBackend(td)
                with self.assertRaises(ProviderError) as ctx:
                    backend.transcribe(b"")
                self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_faster_whisper_transcribe_inference_error(self) -> None:
        from interviewer_domain.adapters.integrations import (
            FasterWhisperLocalBackend,
            ProviderError,
        )

        with tempfile.TemporaryDirectory() as td:
            mock_whisper = MagicMock()
            mock_model = MagicMock()
            mock_model.transcribe.side_effect = RuntimeError("CUDA out of memory")
            mock_whisper.WhisperModel.return_value = mock_model

            with patch.dict(sys.modules, {"faster_whisper": mock_whisper}):
                backend = FasterWhisperLocalBackend(td)
                with self.assertRaises(ProviderError) as ctx:
                    backend.transcribe(b"audio data")
                self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)
                self.assertTrue(ctx.exception.retryable)

    def test_faster_whisper_transcribe_single_segment(self) -> None:
        from interviewer_domain.adapters.integrations import FasterWhisperLocalBackend

        with tempfile.TemporaryDirectory() as td:
            mock_whisper = MagicMock()
            mock_model = MagicMock()
            seg = MagicMock()
            seg.text = "  hello  "
            mock_model.transcribe.return_value = ([seg, seg], {})
            mock_whisper.WhisperModel.return_value = mock_model

            with patch.dict(sys.modules, {"faster_whisper": mock_whisper}):
                backend = FasterWhisperLocalBackend(td)
                result = backend.transcribe(b"audio data")
                self.assertEqual(result, "hello hello")

    def test_faster_whisper_constructor_type_error_fallback(self) -> None:
        from interviewer_domain.adapters.integrations import FasterWhisperLocalBackend

        with tempfile.TemporaryDirectory() as td:
            call_count = 0

            def fake_whisper_model(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise TypeError("unexpected keyword argument 'local_files_only'")
                return MagicMock()

            mock_whisper = MagicMock()
            mock_whisper.WhisperModel.side_effect = fake_whisper_model

            with patch.dict(sys.modules, {"faster_whisper": mock_whisper}):
                FasterWhisperLocalBackend(td)
                self.assertEqual(call_count, 2)

    def test_faster_whisper_constructor_provider_error(self) -> None:
        from interviewer_domain.adapters.integrations import (
            FasterWhisperLocalBackend,
            ProviderError,
        )

        with tempfile.TemporaryDirectory() as td:
            mock_whisper = MagicMock()
            mock_whisper.WhisperModel.side_effect = OSError("model corrupted")

            with patch.dict(sys.modules, {"faster_whisper": mock_whisper}):
                with self.assertRaises(ProviderError) as ctx:
                    FasterWhisperLocalBackend(td)
                self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

    def test_firebase_admin_missing_import_raises_skipped(self) -> None:
        from interviewer_domain.adapters.integrations import (
            FirebaseAdminAuthBackend,
            IntegrationSkipped,
        )

        with self.assertRaises(IntegrationSkipped):
            FirebaseAdminAuthBackend()

    def test_firebase_admin_missing_credentials_raises_skipped(self) -> None:
        from interviewer_domain.adapters.integrations import (
            FirebaseAdminAuthBackend,
            IntegrationSkipped,
        )

        mock_firebase = MagicMock()
        mock_firebase._apps = {}
        mock_auth = MagicMock()
        mock_creds = MagicMock()

        with patch.dict(
            sys.modules,
            {"firebase_admin": mock_firebase, "firebase_admin.auth": mock_auth, "firebase_admin.credentials": mock_creds},
        ):
            with self.assertRaises(IntegrationSkipped):
                FirebaseAdminAuthBackend()

    def test_firebase_admin_verify_empty_token(self) -> None:
        from interviewer_domain.adapters.integrations import (
            FirebaseAdminAuthBackend,
            ProviderError,
        )

        mock_firebase = MagicMock()
        mock_firebase._apps = {"default": True}
        mock_auth = MagicMock()

        with patch.dict(sys.modules, {"firebase_admin": mock_firebase, "firebase_admin.auth": mock_auth}):
            backend = FirebaseAdminAuthBackend.__new__(FirebaseAdminAuthBackend)
            backend._auth = mock_auth
            with self.assertRaises(ProviderError) as ctx:
                backend.verify("")
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_firebase_admin_verify_invalid_token(self) -> None:
        from interviewer_domain.adapters.integrations import (
            FirebaseAdminAuthBackend,
            ProviderError,
        )

        mock_firebase = MagicMock()
        mock_firebase._apps = {"default": True}
        mock_auth = MagicMock()
        mock_auth.verify_id_token.side_effect = ValueError("invalid token")

        with patch.dict(sys.modules, {"firebase_admin": mock_firebase, "firebase_admin.auth": mock_auth}):
            backend = FirebaseAdminAuthBackend.__new__(FirebaseAdminAuthBackend)
            backend._auth = mock_auth
            with self.assertRaises(ProviderError) as ctx:
                backend.verify("bad-token")
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)


class AsyncTransportEdgeCases(unittest.TestCase):
    """Behavioral tests for OpenRouterHTTPTransport with mocked httpx."""

    def test_async_transport_timeout_raises_provider_error(self) -> None:
        import asyncio
        from interviewer_domain.adapters.integrations import OpenRouterHTTPTransport

        async def call() -> None:
            async def fake_post(*args, **kwargs):
                raise asyncio.TimeoutError()

            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {}

            class FakeClient:
                async def post(self, *args, **kwargs):
                    raise asyncio.TimeoutError()
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return False

            transport = OpenRouterHTTPTransport()
            with patch("httpx.AsyncClient", side_effect=lambda **kw: FakeClient()):
                with self.assertRaises(ProviderError) as ctx:
                    await transport.complete({"model": "m"}, "test-key")
                self.assertEqual(ctx.exception.code, ErrorCode.TIMEOUT)
                self.assertTrue(ctx.exception.retryable)

        asyncio.run(call())

    def test_async_transport_generic_error_raises_unavailable(self) -> None:
        import asyncio
        from interviewer_domain.adapters.integrations import OpenRouterHTTPTransport

        async def call() -> None:
            class FakeClient:
                async def post(self, *args, **kwargs):
                    raise ConnectionError("network down")
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return False

            transport = OpenRouterHTTPTransport()
            with patch("httpx.AsyncClient", side_effect=lambda **kw: FakeClient()):
                with self.assertRaises(ProviderError) as ctx:
                    await transport.complete({"model": "m"}, "test-key")
                self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)
                self.assertTrue(ctx.exception.retryable)

        asyncio.run(call())

    def test_async_transport_malformed_response_raises_internal(self) -> None:
        import asyncio
        from interviewer_domain.adapters.integrations import OpenRouterHTTPTransport

        async def call() -> None:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = "not a dict"

            class FakeClient:
                async def post(self, *args, **kwargs):
                    return mock_response
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return False

            transport = OpenRouterHTTPTransport()
            with patch("httpx.AsyncClient", side_effect=lambda **kw: FakeClient()):
                with self.assertRaises(ProviderError) as ctx:
                    await transport.complete({"model": "m"}, "test-key")
                self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

        asyncio.run(call())

    def test_async_transport_successful_response(self) -> None:
        import asyncio
        from interviewer_domain.adapters.integrations import OpenRouterHTTPTransport

        async def call() -> None:
            expected = {"choices": [{"message": {"content": "ok"}}]}
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = expected

            class FakeClient:
                async def post(self, *args, **kwargs):
                    return mock_response
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return False

            transport = OpenRouterHTTPTransport()
            with patch("httpx.AsyncClient", side_effect=lambda **kw: FakeClient()):
                result = await transport.complete({"model": "m"}, "test-key")
            self.assertEqual(result, expected)

        asyncio.run(call())


class OpenRouterEvaluatorEdgeCases(unittest.TestCase):
    """Behavioral edge cases for the OpenRouterEvaluator adapter."""

    def test_evaluate_empty_api_key_raises_invalid_request(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        transport = MagicMock()
        evaluator = OpenRouterEvaluator(transport, api_key="", model="gpt-4")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        transcript = (TranscriptSegment(uuid4(), "candidate", "Hello"),)
        with self.assertRaises(ProviderError) as ctx:
            evaluator.evaluate(context, transcript)
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_evaluate_empty_model_raises_invalid_request(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        transport = MagicMock()
        evaluator = OpenRouterEvaluator(transport, api_key="key", model="")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        transcript = (TranscriptSegment(uuid4(), "candidate", "Hello"),)
        with self.assertRaises(ProviderError) as ctx:
            evaluator.evaluate(context, transcript)
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_evaluate_empty_transcript_raises_invalid_request(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        transport = MagicMock()
        evaluator = OpenRouterEvaluator(transport, api_key="key", model="gpt-4")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        with self.assertRaises(ProviderError) as ctx:
            evaluator.evaluate(context, ())
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_evaluate_malformed_response_raises_internal(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        transport = MagicMock()
        transport.complete.return_value = {}
        evaluator = OpenRouterEvaluator(transport, api_key="key", model="gpt-4")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        transcript = (TranscriptSegment(uuid4(), "candidate", "Hello"),)
        with self.assertRaises(ProviderError) as ctx:
            evaluator.evaluate(context, transcript)
        self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

    def test_evaluate_non_dict_response_raises_internal(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        transport = MagicMock()
        transport.complete.return_value = {"choices": [{"message": {"content": 42}}]}
        evaluator = OpenRouterEvaluator(transport, api_key="key", model="gpt-4")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        transcript = (TranscriptSegment(uuid4(), "candidate", "Hello"),)
        with self.assertRaises(ProviderError) as ctx:
            evaluator.evaluate(context, transcript)
        self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

    def test_evaluate_dict_dimensions_normalizes(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        response_payload = {
            "choices": [{"message": {"content": json.dumps({
                "score": 80,
                "dimensions": {"communication": "clear", "technical": "solid"},
                "summary": "Good",
                "strengths": ["clear"],
                "weaknesses": [],
                "recommendations": [],
            })}}]
        }
        transport = MagicMock()
        transport.complete.return_value = response_payload
        evaluator = OpenRouterEvaluator(transport, api_key="key", model="gpt-4")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        transcript = (TranscriptSegment(uuid4(), "candidate", "Hello"),)
        result = evaluator.evaluate(context, transcript)
        self.assertEqual(result.score, 80)
        self.assertEqual(len(result.dimensions), 2)

    def test_evaluate_list_dimensions_with_strings_normalizes(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        response_payload = {
            "choices": [{"message": {"content": json.dumps({
                "score": 70,
                "dimensions": ["good communication", "solid technical"],
                "summary": "Good",
                "strengths": [],
                "weaknesses": [],
                "recommendations": [],
            })}}]
        }
        transport = MagicMock()
        transport.complete.return_value = response_payload
        evaluator = OpenRouterEvaluator(transport, api_key="key", model="gpt-4")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        transcript = (TranscriptSegment(uuid4(), "candidate", "Hello"),)
        result = evaluator.evaluate(context, transcript)
        self.assertEqual(result.score, 70)
        self.assertEqual(len(result.dimensions), 2)

    def test_evaluate_empty_dimensions_raises_internal(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        response_payload = {
            "choices": [{"message": {"content": json.dumps({
                "score": 70,
                "dimensions": [],
                "summary": "Good",
            })}}]
        }
        transport = MagicMock()
        transport.complete.return_value = response_payload
        evaluator = OpenRouterEvaluator(transport, api_key="key", model="gpt-4")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        transcript = (TranscriptSegment(uuid4(), "candidate", "Hello"),)
        with self.assertRaises(ProviderError) as ctx:
            evaluator.evaluate(context, transcript)
        self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)

    def test_evaluate_string_dimensions_raises_internal(self) -> None:
        from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
        from interviewer_domain.evaluation import InterviewContext

        response_payload = {
            "choices": [{"message": {"content": json.dumps({
                "score": 70,
                "dimensions": "not a list or dict",
                "summary": "Good",
            })}}]
        }
        transport = MagicMock()
        transport.complete.return_value = response_payload
        evaluator = OpenRouterEvaluator(transport, api_key="key", model="gpt-4")
        context = InterviewContext(InterviewMode.RECRUITER, "Engineer", "mid")
        transcript = (TranscriptSegment(uuid4(), "candidate", "Hello"),)
        with self.assertRaises(ProviderError) as ctx:
            evaluator.evaluate(context, transcript)
        self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)


class DocumentParserEdgeCases(unittest.TestCase):
    """Behavioral edge cases for LocalDocumentParser missing paths."""

    def test_parse_empty_content_raises_invalid_request(self) -> None:
        from interviewer_domain.documents import LocalDocumentParser

        parser = LocalDocumentParser()
        with self.assertRaises(ProviderError) as ctx:
            parser.parse(b"", "text/plain", "job_description")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_parse_resume_non_pdf_raises_invalid_request(self) -> None:
        from interviewer_domain.documents import LocalDocumentParser

        parser = LocalDocumentParser()
        with self.assertRaises(ProviderError) as ctx:
            parser.parse(b"not a pdf", "application/pdf", "resume")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_parse_resume_wrong_content_type_raises_invalid_request(self) -> None:
        from interviewer_domain.documents import LocalDocumentParser

        parser = LocalDocumentParser()
        with self.assertRaises(ProviderError) as ctx:
            parser.parse(b"some content", "text/plain", "resume")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_parse_jd_non_text_content_type_raises_invalid_request(self) -> None:
        from interviewer_domain.documents import LocalDocumentParser

        parser = LocalDocumentParser()
        with self.assertRaises(ProviderError) as ctx:
            parser.parse(b"some content", "application/octet-stream", "job_description")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_parse_unsupported_source_raises_invalid_request(self) -> None:
        from interviewer_domain.documents import LocalDocumentParser

        parser = LocalDocumentParser()
        with self.assertRaises(ProviderError) as ctx:
            parser.parse(b"some content", "text/plain", "unsupported_source")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_parse_pdf_no_extractable_text_raises_invalid_request(self) -> None:
        from interviewer_domain.documents import LocalDocumentParser

        parser = LocalDocumentParser()
        with self.assertRaises(ProviderError) as ctx:
            parser.parse(b"%PDF-1.7\nno text here\n%%EOF", "application/pdf", "resume")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_replace_chunk_text_truncates_to_max_length(self) -> None:
        from interviewer_domain.documents import MAX_CHUNK_LENGTH, replace_chunk_text
        from interviewer_domain.models import DocumentChunk, DocumentSource

        chunk = DocumentChunk(DocumentSource.RESUME, "section", "original", "line:1")
        long_text = "x" * (MAX_CHUNK_LENGTH + 100)
        result = replace_chunk_text(chunk, long_text)
        self.assertEqual(len(result.text), MAX_CHUNK_LENGTH)


class ModelsEdgeCases(unittest.TestCase):
    """Behavioral edge cases for model validation."""

    def test_turn_invalid_speaker_raises_value_error(self) -> None:
        from interviewer_domain.models import Turn

        with self.assertRaises(ValueError) as ctx:
            Turn(session_id=uuid4(), sequence=1, speaker="invalid")
        self.assertIn("speaker", str(ctx.exception))

    def test_turn_invalid_sequence_raises_value_error(self) -> None:
        from interviewer_domain.models import Turn

        with self.assertRaises(ValueError) as ctx:
            Turn(session_id=uuid4(), sequence=0, speaker="candidate")
        self.assertIn("sequence", str(ctx.exception))

    def test_evaluation_score_out_of_range_raises_value_error(self) -> None:
        from interviewer_domain.models import Evaluation

        with self.assertRaises(ValueError) as ctx:
            Evaluation(session_id=uuid4(), rubric_version="v1", score=150)
        self.assertIn("score", str(ctx.exception))

    def test_evaluation_negative_score_raises_value_error(self) -> None:
        from interviewer_domain.models import Evaluation

        with self.assertRaises(ValueError) as ctx:
            Evaluation(session_id=uuid4(), rubric_version="v1", score=-10)
        self.assertIn("score", str(ctx.exception))

    def test_evaluation_weights_not_summing_to_one_raises_value_error(self) -> None:
        from interviewer_domain.models import Evaluation

        with self.assertRaises(ValueError) as ctx:
            Evaluation(
                session_id=uuid4(),
                rubric_version="v1",
                score=80,
                dimensions=({"weight": 0.5}, {"weight": 0.7}),
            )
        self.assertIn("weights", str(ctx.exception))

    def test_evaluation_dimension_score_out_of_range_raises_value_error(self) -> None:
        from interviewer_domain.models import Evaluation

        with self.assertRaises(ValueError) as ctx:
            Evaluation(
                session_id=uuid4(),
                rubric_version="v1",
                score=80,
                dimensions=({"score": 150},),
            )
        self.assertIn("scores", str(ctx.exception))


class SessionEdgeCases(unittest.TestCase):
    """Behavioral edge cases for session engine error paths."""

    def test_cancel_active_session(self) -> None:
        from interviewer_domain.session import InterviewSessionEngine, QuestionPlanner
        from interviewer_domain.models import InterviewSession, InterviewMode

        session = InterviewSession(user_id="alice", mode=InterviewMode.RECRUITER)

        class FakeSTT:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("stt", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def transcribe(self, audio, turn_id, token):
                pass

        class FakeLLM:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("llm", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def generate(self, prompt, token):
                return "response"

        class FakeTTS:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("tts", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def synthesize(self, text, token):
                return b"audio"

        class FakeDataStore:
            def link_turn_session(self, turn_id, session_id):
                pass
            def save_transcript(self, segment):
                pass
            def save_recording(self, recording):
                pass
            def list_transcript(self, session_id):
                return []

        class FakeEventBus:
            async def publish(self, event):
                pass

        engine = InterviewSessionEngine(session, FakeSTT(), FakeLLM(), FakeTTS(), FakeDataStore(), FakeEventBus())

        async def call() -> None:
            await engine.start()
            self.assertEqual(engine.session.status, "active")
            await engine.cancel()
            self.assertEqual(engine.session.status, "cancelled")

        asyncio.run(call())

    def test_process_turn_wrong_session_raises_state_error(self) -> None:
        from interviewer_domain.session import InterviewSessionEngine, SessionStateError
        from interviewer_domain.models import InterviewSession, InterviewMode, Turn

        session = InterviewSession(user_id="alice", mode=InterviewMode.RECRUITER)

        class FakeSTT:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("stt", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def transcribe(self, audio, turn_id, token):
                pass

        class FakeLLM:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("llm", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def generate(self, prompt, token):
                return "response"

        class FakeTTS:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("tts", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def synthesize(self, text, token):
                return b"audio"

        class FakeDataStore:
            def link_turn_session(self, turn_id, session_id):
                pass
            def save_transcript(self, segment):
                pass
            def save_recording(self, recording):
                pass
            def list_transcript(self, session_id):
                return []

        class FakeEventBus:
            async def publish(self, event):
                pass

        engine = InterviewSessionEngine(session, FakeSTT(), FakeLLM(), FakeTTS(), FakeDataStore(), FakeEventBus())

        async def call() -> None:
            await engine.start()
            wrong_turn = Turn(session_id=uuid4(), sequence=1, speaker="candidate", input_audio=b"audio")
            with self.assertRaises(SessionStateError):
                await engine.process_turn(wrong_turn)

        asyncio.run(call())

    def test_process_turn_wrong_speaker_raises_state_error(self) -> None:
        from interviewer_domain.session import InterviewSessionEngine, SessionStateError
        from interviewer_domain.models import InterviewSession, InterviewMode, Turn

        session = InterviewSession(user_id="alice", mode=InterviewMode.RECRUITER)

        class FakeSTT:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("stt", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def transcribe(self, audio, turn_id, token):
                pass

        class FakeLLM:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("llm", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def generate(self, prompt, token):
                return "response"

        class FakeTTS:
            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor
                return CapabilityDescriptor("tts", False, False)
            async def health(self):
                from interviewer_domain.contracts import HealthStatus
                return HealthStatus(True)
            async def synthesize(self, text, token):
                return b"audio"

        class FakeDataStore:
            def link_turn_session(self, turn_id, session_id):
                pass
            def save_transcript(self, segment):
                pass
            def save_recording(self, recording):
                pass
            def list_transcript(self, session_id):
                return []

        class FakeEventBus:
            async def publish(self, event):
                pass

        engine = InterviewSessionEngine(session, FakeSTT(), FakeLLM(), FakeTTS(), FakeDataStore(), FakeEventBus())

        async def call() -> None:
            await engine.start()
            wrong_turn = Turn(session_id=session.id, sequence=1, speaker="interviewer", input_audio=b"audio")
            with self.assertRaises(SessionStateError):
                await engine.process_turn(wrong_turn)

        asyncio.run(call())


class InMemoryProviderEdgeCases(unittest.TestCase):
    """Behavioral edge cases for in-memory provider error paths."""

    def test_in_memory_llm_empty_prompt_raises_invalid_request(self) -> None:
        from interviewer_domain.providers import InMemoryLLM

        llm = InMemoryLLM()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await llm.generate("", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_in_memory_tts_empty_text_raises_invalid_request(self) -> None:
        from interviewer_domain.providers import InMemoryTTS

        tts = InMemoryTTS()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await tts.synthesize("", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_in_memory_storage_get_missing_key(self) -> None:
        from interviewer_domain.providers import InMemoryStorage

        storage = InMemoryStorage()
        with self.assertRaises(ProviderError) as ctx:
            storage.get("nonexistent")
        self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

    def test_in_memory_storage_delete_prefix_with_non_matching_key(self) -> None:
        from interviewer_domain.providers import InMemoryStorage

        storage = InMemoryStorage()
        storage.put("other/something", b"data", "text/plain")
        storage.delete_prefix("nonexistent/")
        self.assertIn("other/something", storage.files)

    def test_in_memory_streaming_stt_empty_audio(self) -> None:
        from interviewer_domain.providers import InMemoryStreamingSTT

        stt = InMemoryStreamingSTT()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                async for _ in stt.transcribe_stream(b"", uuid4(), CancellationToken()):
                    pass
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_in_memory_streaming_llm_empty_prompt(self) -> None:
        from interviewer_domain.providers import InMemoryStreamingLLM

        llm = InMemoryStreamingLLM()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                async for _ in llm.generate_stream("", CancellationToken()):
                    pass
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_in_memory_secondary_response_empty_answer(self) -> None:
        from interviewer_domain.providers import InMemorySecondaryResponse

        secondary = InMemorySecondaryResponse()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await secondary.generate_secondary("", CancellationToken())
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_in_memory_streaming_tts_empty_text(self) -> None:
        from interviewer_domain.providers import InMemoryStreamingTTS

        tts = InMemoryStreamingTTS()

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                async for _ in tts.synthesize_stream("", CancellationToken()):
                    pass
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())


class ConfigurationEdgeCases(unittest.TestCase):
    """Behavioral edge cases for configuration validation and parsing functions."""

    def test_invalid_app_profile_raises_configuration_error(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({"APP_PROFILE": "invalid-profile"})
        self.assertIn("APP_PROFILE", str(ctx.exception))

    def test_invalid_storage_backend_raises_configuration_error(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({"STORAGE_BACKEND": "azure"})
        self.assertIn("STORAGE_BACKEND", str(ctx.exception))

    def test_non_integer_retention_days_raises_configuration_error(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({"RETENTION_DAYS": "not-a-number"})
        self.assertIn("RETENTION_DAYS", str(ctx.exception))

    def test_retention_days_below_minimum_raises_configuration_error(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({"RETENTION_DAYS": "0"})
        self.assertIn("RETENTION_DAYS", str(ctx.exception))

    def test_non_numeric_health_timeout_raises_configuration_error(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({"HEALTH_TIMEOUT_SECONDS": "abc"})
        self.assertIn("HEALTH_TIMEOUT_SECONDS", str(ctx.exception))

    def test_health_timeout_below_minimum_raises_configuration_error(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({"HEALTH_TIMEOUT_SECONDS": "0.01"})
        self.assertIn("HEALTH_TIMEOUT_SECONDS", str(ctx.exception))

    def test_invalid_boolean_metrics_raises_configuration_error(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({"METRICS_ENABLED": "maybe"})
        self.assertIn("METRICS_ENABLED", str(ctx.exception))

    def test_boolean_true_values_accepted(self) -> None:
        from interviewer_domain.configuration import RuntimeSettings

        for value in ("true", "1", "yes", "True", "YES"):
            settings = RuntimeSettings.from_env({"METRICS_ENABLED": value, "TRACING_ENABLED": value})
            self.assertTrue(settings.metrics_enabled)
            self.assertTrue(settings.tracing_enabled)

    def test_boolean_false_values_accepted(self) -> None:
        from interviewer_domain.configuration import RuntimeSettings

        for value in ("false", "0", "no", "False", "NO"):
            settings = RuntimeSettings.from_env({"METRICS_ENABLED": value, "TRACING_ENABLED": value})
            self.assertFalse(settings.metrics_enabled)
            self.assertFalse(settings.tracing_enabled)

    def test_production_missing_storage_bucket_with_non_local_backend(self) -> None:
        from interviewer_domain.configuration import ConfigurationError

        with self.assertRaises(ConfigurationError) as ctx:
            from interviewer_domain.configuration import RuntimeSettings

            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "faster-whisper",
                "TTS_PROVIDER": "piper",
                "LLM_PROVIDER": "openrouter",
                "LLM_API_KEY": "key",
                "STORAGE_BACKEND": "s3",
            })
        self.assertIn("STORAGE_BUCKET", str(ctx.exception))

    def test_production_missing_stt_api_key_for_groq_provider(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "groq",
                "TTS_PROVIDER": "in-memory",
                "LLM_PROVIDER": "in-memory",
            })
        self.assertIn("STT_API_KEY", str(ctx.exception))

    def test_production_missing_tts_api_key_for_hosted_provider(self) -> None:
        from interviewer_domain.configuration import ConfigurationError

        with self.assertRaises(ConfigurationError) as ctx:
            from interviewer_domain.configuration import RuntimeSettings

            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "in-memory",
                "TTS_PROVIDER": "hosted",
                "LLM_PROVIDER": "in-memory",
            })
        self.assertIn("TTS_API_KEY", str(ctx.exception))

    def test_production_unrecognized_stt_provider(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "unknown-stt",
                "STT_FALLBACK_PROVIDER": "in-memory",
                "TTS_PROVIDER": "piper",
                "TTS_FALLBACK_PROVIDER": "in-memory",
                "LLM_PROVIDER": "openrouter",
                "LLM_FALLBACK_PROVIDER": "in-memory",
                "LLM_API_KEY": "key",
            })
        self.assertIn("STT_PROVIDER", str(ctx.exception))

    def test_production_unrecognized_tts_provider(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "faster-whisper",
                "STT_FALLBACK_PROVIDER": "in-memory",
                "TTS_PROVIDER": "unknown-tts",
                "TTS_FALLBACK_PROVIDER": "in-memory",
                "LLM_PROVIDER": "openrouter",
                "LLM_FALLBACK_PROVIDER": "in-memory",
                "LLM_API_KEY": "key",
            })
        self.assertIn("TTS_PROVIDER", str(ctx.exception))

    def test_production_unrecognized_llm_provider(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "faster-whisper",
                "STT_FALLBACK_PROVIDER": "in-memory",
                "TTS_PROVIDER": "piper",
                "TTS_FALLBACK_PROVIDER": "in-memory",
                "LLM_PROVIDER": "unknown-llm",
                "LLM_FALLBACK_PROVIDER": "in-memory",
            })
        self.assertIn("LLM_PROVIDER", str(ctx.exception))

    def test_production_unrecognized_stt_fallback_provider(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "faster-whisper",
                "STT_FALLBACK_PROVIDER": "unknown",
                "TTS_PROVIDER": "piper",
                "TTS_FALLBACK_PROVIDER": "in-memory",
                "LLM_PROVIDER": "openrouter",
                "LLM_FALLBACK_PROVIDER": "in-memory",
                "LLM_API_KEY": "key",
            })
        self.assertIn("STT_FALLBACK_PROVIDER", str(ctx.exception))

    def test_production_unrecognized_tts_fallback_provider(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "faster-whisper",
                "STT_FALLBACK_PROVIDER": "in-memory",
                "TTS_PROVIDER": "piper",
                "TTS_FALLBACK_PROVIDER": "unknown",
                "LLM_PROVIDER": "openrouter",
                "LLM_FALLBACK_PROVIDER": "in-memory",
                "LLM_API_KEY": "key",
            })
        self.assertIn("TTS_FALLBACK_PROVIDER", str(ctx.exception))

    def test_production_unrecognized_llm_fallback_provider(self) -> None:
        from interviewer_domain.configuration import ConfigurationError, RuntimeSettings

        with self.assertRaises(ConfigurationError) as ctx:
            RuntimeSettings.from_env({
                "APP_PROFILE": "production",
                "FIREBASE_PROJECT_ID": "proj",
                "FIRESTORE_DATABASE": "(default)",
                "STT_PROVIDER": "faster-whisper",
                "STT_FALLBACK_PROVIDER": "in-memory",
                "TTS_PROVIDER": "piper",
                "TTS_FALLBACK_PROVIDER": "in-memory",
                "LLM_PROVIDER": "openrouter",
                "LLM_FALLBACK_PROVIDER": "unknown",
                "LLM_API_KEY": "key",
            })
        self.assertIn("LLM_FALLBACK_PROVIDER", str(ctx.exception))

    def test_compose_providers_faster_whisper_backend_auto_creation(self) -> None:
        from interviewer_domain.configuration import RuntimeSettings, compose_providers

        settings = RuntimeSettings.from_env({
            "APP_PROFILE": "production",
            "FIREBASE_PROJECT_ID": "proj",
            "FIRESTORE_DATABASE": "(default)",
            "STT_PROVIDER": "faster-whisper",
            "STT_FALLBACK_PROVIDER": "in-memory",
            "TTS_PROVIDER": "piper",
            "TTS_FALLBACK_PROVIDER": "in-memory",
            "LLM_PROVIDER": "openrouter",
            "LLM_FALLBACK_PROVIDER": "in-memory",
            "LLM_API_KEY": "key",
        })
        providers = compose_providers(settings)
        self.assertEqual(providers.stt[0].capabilities().name, "faster-whisper")

    def test_compose_providers_piper_backend_auto_creation(self) -> None:
        from interviewer_domain.configuration import RuntimeSettings, compose_providers

        settings = RuntimeSettings.from_env({
            "APP_PROFILE": "production",
            "FIREBASE_PROJECT_ID": "proj",
            "FIRESTORE_DATABASE": "(default)",
            "STT_PROVIDER": "faster-whisper",
            "STT_FALLBACK_PROVIDER": "in-memory",
            "TTS_PROVIDER": "piper",
            "TTS_FALLBACK_PROVIDER": "in-memory",
            "LLM_PROVIDER": "openrouter",
            "LLM_FALLBACK_PROVIDER": "in-memory",
            "LLM_API_KEY": "key",
        })
        providers = compose_providers(settings)
        self.assertEqual(providers.tts[0].capabilities().name, "piper-kokoro")

    def test_compose_providers_openrouter_auto_creation(self) -> None:
        from interviewer_domain.configuration import RuntimeSettings, compose_providers

        settings = RuntimeSettings.from_env({
            "APP_PROFILE": "production",
            "FIREBASE_PROJECT_ID": "proj",
            "FIRESTORE_DATABASE": "(default)",
            "STT_PROVIDER": "faster-whisper",
            "STT_FALLBACK_PROVIDER": "in-memory",
            "TTS_PROVIDER": "piper",
            "TTS_FALLBACK_PROVIDER": "in-memory",
            "LLM_PROVIDER": "openrouter",
            "LLM_FALLBACK_PROVIDER": "in-memory",
            "LLM_API_KEY": "test-key",
        })
        providers = compose_providers(settings)
        self.assertEqual(providers.llm[0].capabilities().name, "openrouter")

    def test_readiness_checker_required_unhealthy_raises(self) -> None:
        from interviewer_domain.configuration import (
            ConfigurationError,
            ProviderReadinessChecker,
            RuntimeProviders,
        )

        class UnhealthyProvider:
            async def health(self):
                from interviewer_domain.contracts import HealthStatus

                return HealthStatus(False, "not ready")

            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor

                return CapabilityDescriptor("test", False, False)

        providers = RuntimeProviders(
            (UnhealthyProvider(),),
            (UnhealthyProvider(),),
            (UnhealthyProvider(),),
        )
        checker = ProviderReadinessChecker(providers, required=True)

        async def call() -> None:
            with self.assertRaises(ConfigurationError) as ctx:
                await checker.check()
            self.assertIn("not healthy", str(ctx.exception))

        asyncio.run(call())

    def test_readiness_checker_optional_unhealthy_succeeds(self) -> None:
        from interviewer_domain.configuration import (
            ProviderReadinessChecker,
            RuntimeProviders,
        )

        class UnhealthyProvider:
            async def health(self):
                from interviewer_domain.contracts import HealthStatus

                return HealthStatus(False, "not ready")

            def capabilities(self):
                from interviewer_domain.contracts import CapabilityDescriptor

                return CapabilityDescriptor("test", False, False)

        providers = RuntimeProviders(
            (UnhealthyProvider(),),
            (UnhealthyProvider(),),
            (UnhealthyProvider(),),
        )
        checker = ProviderReadinessChecker(providers, required=False)

        async def call() -> None:
            reports = await checker.check()
            self.assertEqual(len(reports), 3)
            self.assertFalse(all(r.healthy for r in reports))

        asyncio.run(call())

    def test_skip_reason_all_profiles(self) -> None:
        from interviewer_domain.adapters.integrations import skip_reason

        self.assertIn("STT_MODEL", skip_reason("faster-whisper", {}))
        self.assertIn("TTS_MODEL", skip_reason("piper", {}))
        self.assertIn("FIREBASE_PROJECT_ID", skip_reason("firestore", {}))
        self.assertIn("STORAGE_BUCKET", skip_reason("storage", {}))
        self.assertIn("PHASE15_BROWSER_URL", skip_reason("webrtc", {}))
        self.assertEqual(skip_reason("unknown-profile", {}), "profile is configured")

    def test_configured_profiles_with_multiple_values(self) -> None:
        from interviewer_domain.adapters.integrations import configured_profiles

        self.assertEqual(
            configured_profiles({"PHASE15_PROFILES": "openrouter, piper , "}),
            ("openrouter", "piper"),
        )
        self.assertEqual(
            configured_profiles({"PHASE15_PROFILES": "  "}),
            (),
        )


class PersistenceEdgeCases(unittest.TestCase):
    """Behavioral edge cases for persistence adapters."""

    def test_interview_record_retention_negative_days(self) -> None:
        from interviewer_domain.persistence import InterviewRecord

        record = InterviewRecord("alice", InterviewMode.RECRUITER)
        with self.assertRaises(ValueError) as ctx:
            record.with_retention(days=-1)
        self.assertIn("retention", str(ctx.exception))

    def test_interview_record_retention_zero_days(self) -> None:
        from interviewer_domain.persistence import InterviewRecord

        record = InterviewRecord("alice", InterviewMode.RECRUITER)
        with self.assertRaises(ValueError):
            record.with_retention(days=0)

    def test_firebase_auth_adapter_empty_token(self) -> None:
        from interviewer_domain.persistence import FirebaseAuthAdapter

        class FakeBackend:
            def verify(self, token):
                return {}

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await FirebaseAuthAdapter(FakeBackend()).validate("")
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_firebase_auth_adapter_missing_uid(self) -> None:
        from interviewer_domain.persistence import FirebaseAuthAdapter

        class FakeBackend:
            def verify(self, token):
                return {"sub": "user123"}

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await FirebaseAuthAdapter(FakeBackend()).validate("token")
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_firebase_auth_adapter_empty_uid(self) -> None:
        from interviewer_domain.persistence import FirebaseAuthAdapter

        class FakeBackend:
            def verify(self, token):
                return {"uid": ""}

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await FirebaseAuthAdapter(FakeBackend()).validate("token")
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_firebase_auth_adapter_none_claims(self) -> None:
        from interviewer_domain.persistence import FirebaseAuthAdapter

        class FakeBackend:
            def verify(self, token):
                return None

        async def call() -> None:
            with self.assertRaises(ProviderError) as ctx:
                await FirebaseAuthAdapter(FakeBackend()).validate("token")
            self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

        asyncio.run(call())

    def test_local_filesystem_storage_get_missing_key(self) -> None:
        from interviewer_domain.persistence import LocalFilesystemStorage

        with tempfile.TemporaryDirectory() as td:
            storage = LocalFilesystemStorage(td)
            with self.assertRaises(ProviderError) as ctx:
                storage.get("nonexistent/file.pdf")
            self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

    def test_s3_storage_get_missing_key(self) -> None:
        from interviewer_domain.persistence import S3CompatibleStorage

        class FakeBackend:
            def get_object(self, key):
                raise KeyError(key)

        with self.assertRaises(ProviderError) as ctx:
            S3CompatibleStorage(FakeBackend()).get("missing-key")
        self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

    def test_rate_limiter_negative_limit_raises(self) -> None:
        from interviewer_domain.persistence import FixedWindowRateLimiter

        with self.assertRaises(ValueError) as ctx:
            FixedWindowRateLimiter(limit=-1, window_seconds=60)
        self.assertIn("positive", str(ctx.exception))

    def test_rate_limiter_negative_window_raises(self) -> None:
        from interviewer_domain.persistence import FixedWindowRateLimiter

        with self.assertRaises(ValueError) as ctx:
            FixedWindowRateLimiter(limit=10, window_seconds=-1)
        self.assertIn("positive", str(ctx.exception))

    def test_rate_limiter_window_expiration_resets(self) -> None:
        from interviewer_domain.persistence import FixedWindowRateLimiter

        limiter = FixedWindowRateLimiter(limit=2, window_seconds=60)
        t1 = datetime(2027, 1, 1, tzinfo=timezone.utc)
        t2 = t1 + timedelta(seconds=61)
        self.assertTrue(limiter.allow("alice", t1))
        self.assertTrue(limiter.allow("alice", t1))
        self.assertFalse(limiter.allow("alice", t1))
        self.assertTrue(limiter.allow("alice", t2))

    def test_firestore_data_store_get_interview_not_found(self) -> None:
        from interviewer_domain.persistence import FirestoreDataStore

        class FakeBackend:
            def get(self, collection, document_id):
                return None

        store = FirestoreDataStore(FakeBackend())
        with self.assertRaises(ProviderError) as ctx:
            store.get_interview("alice", uuid4())
        self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

    def test_firestore_data_store_delete_interview_not_found(self) -> None:
        from interviewer_domain.persistence import FirestoreDataStore

        class FakeBackend:
            def get(self, collection, document_id):
                return None

        store = FirestoreDataStore(FakeBackend())
        with self.assertRaises(ProviderError) as ctx:
            store.delete_interview("alice", uuid4())
        self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

    def test_firestore_data_store_get_evaluation_not_found(self) -> None:
        from interviewer_domain.persistence import FirestoreDataStore, InterviewRecord

        class FakeBackend:
            def __init__(self):
                self.data = {}

            def set(self, collection, document_id, value):
                self.data[(collection, document_id)] = value

            def get(self, collection, document_id):
                return self.data.get((collection, document_id))

            def list(self, collection, field, value):
                return []

        backend = FakeBackend()
        store = FirestoreDataStore(backend)
        record = InterviewRecord(
            "alice", InterviewMode.RECRUITER,
            created_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
        )
        store.save_interview(record)
        result = store.get_evaluation("alice", record.id)
        self.assertIsNone(result)

    def test_persistence_service_results_view_with_evaluation(self) -> None:
        from interviewer_domain.persistence import (
            InMemoryPersistentDataStore,
            LocalFilesystemStorage,
            PersistenceService,
        )

        now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        data = InMemoryPersistentDataStore()
        with tempfile.TemporaryDirectory() as td:
            service = PersistenceService(data, LocalFilesystemStorage(td))
            record = service.create_interview("alice", InterviewMode.TECHNICAL, now)
            data.save_evaluation(
                "alice",
                record.id,
                Evaluation(record.id, "v1", 85, ("design",), "technical", {}, "Good", ("clear",), ("brief",), ("more detail",)),
            )
            resource = service.resource("alice", "results", record.id, now=now)
            self.assertIn("evaluation", resource.payload)

    def test_upload_validator_content_type_mismatch(self) -> None:
        from interviewer_domain.persistence import UploadValidator

        validator = UploadValidator()
        with self.assertRaises(ProviderError) as ctx:
            validator.validate_resume("resume.pdf", b"%PDF-content", "text/plain")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_REQUEST)

    def test_in_memory_data_store_get_interview_expired(self) -> None:
        from interviewer_domain.persistence import InMemoryPersistentDataStore, InterviewRecord

        data = InMemoryPersistentDataStore()
        record = InterviewRecord(
            "alice",
            InterviewMode.RECRUITER,
            created_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
            expires_at=datetime(2027, 1, 5, tzinfo=timezone.utc),
        )
        data.save_interview(record)
        now = datetime(2027, 1, 10, tzinfo=timezone.utc)
        with self.assertRaises(ProviderError) as ctx:
            data.get_interview("alice", record.id, now)
        self.assertEqual(ctx.exception.code, ErrorCode.UNAVAILABLE)

    def test_in_memory_data_store_get_evaluation_expired(self) -> None:
        from interviewer_domain.persistence import InMemoryPersistentDataStore, InterviewRecord

        data = InMemoryPersistentDataStore()
        record = InterviewRecord(
            "alice",
            InterviewMode.RECRUITER,
            created_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
            expires_at=datetime(2027, 1, 5, tzinfo=timezone.utc),
        )
        data.save_interview(record)
        data.save_evaluation("alice", record.id, Evaluation(record.id, "v1", 80))
        now = datetime(2027, 1, 10, tzinfo=timezone.utc)
        result = data.get_evaluation("alice", record.id, now)
        self.assertIsNone(result)


# Need httpx import for the sync transport test (it's used in the mock side_effect)
try:
    import httpx
except ImportError:
    httpx = MagicMock()


if __name__ == "__main__":
    unittest.main()
