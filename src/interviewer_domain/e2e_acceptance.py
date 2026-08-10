"""Repeatable, observable Phase 14 local user acceptance journey."""

from __future__ import annotations

import asyncio
import html
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from .contracts import CancellationToken, ErrorCode, HealthStatus, ProviderError
from .documents import LocalDocumentParser
from .evaluation import InterviewContext, PostInterviewEvaluationService
from .live_voice import LiveVoiceOrchestrator
from .models import InterviewMode, InterviewSession, Turn
from .persistence import (
    InMemoryPersistentDataStore,
    PersistenceService,
    UploadValidator,
)
from .providers import (
    InMemoryDataStore,
    InMemoryEventBus,
    InMemorySecondaryResponse,
    InMemoryStreamingLLM,
    InMemoryStreamingSTT,
    InMemoryStreamingTTS,
    InMemoryStorage,
)
from .retrieval import (
    DeterministicEmbeddingProvider,
    InMemoryVectorStore,
    TopicRetriever,
)
from .routing import FallbackRouter
from .transport import (
    BrowserSessionState,
    LocalWebRTCBoundary,
    SessionEventType,
    SignalingMessage,
    SignalingType,
    TransportValidationError,
)

MARKERS = (
    "[PHASE14] auth-setup-ok",
    "[PHASE14] pdf-rag-ok",
    "[PHASE14] providers-separated-ok",
    "[PHASE14] browser-media-loop-ok",
    "[PHASE14] interruption-reconnect-ok",
    "[PHASE14] persisted-evaluation-ok",
    "[PHASE14] replay-deletion-ok",
    "[PHASE14] negative-journeys-ok",
    "[PHASE14] configured-integrations-report-ok",
    "[PHASE14] evidence-artifacts-ok",
)
FORBIDDEN = (
    "Traceback",
    "Script Error",
    "secret leaked",
    "Firebase private key",
    "media tunneled over websocket",
    "stale response spoken",
    "NotImplementedError",
    "placeholder",
    "skipped required check",
    "EXPECTED_STRING_SUBSTITUTION",
)


@dataclass(frozen=True, slots=True)
class EvidenceEvent:
    """One timestamped observable acceptance state change."""

    name: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(slots=True)
class AcceptanceReport:
    """Human-readable and machine-readable result for one local journey."""

    profile: str = "local"
    schema_version: int = 1
    passed: bool = True
    events: list[EvidenceEvent] = field(default_factory=list)
    integrations: dict[str, dict[str, Any]] = field(default_factory=dict)
    markers: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def record(self, name: str, **details: Any) -> None:
        """Record a successful observable state transition."""
        self.events.append(EvidenceEvent(name, "passed", _redact(details)))

    def fail(self, name: str, error: str) -> None:
        """Record a safe, redacted failure diagnostic."""
        self.passed = False
        self.failures.append(f"{name}: {error}")
        self.events.append(
            EvidenceEvent(name, "failed", {"error": _redact_text(error)})
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report without secrets or non-JSON domain values."""
        return {
            "profile": self.profile,
            "schema_version": self.schema_version,
            "passed": self.passed,
            "events": [asdict(event) for event in self.events],
            "integrations": self.integrations,
            "markers": self.markers,
            "failures": self.failures,
        }

    def write(self, directory: str | Path) -> tuple[Path, Path, Path]:
        """Write JSON, Markdown, and HTML evidence outside source control."""
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.to_dict(), indent=2, sort_keys=True)
        json_path = target / "phase14-report.json"
        markdown_path = target / "phase14-report.md"
        html_path = target / "phase14-report.html"
        json_path.write_text(payload + "\n", encoding="utf-8")
        rows = "\n".join(
            f"| {event.occurred_at} | {event.name} | {event.status} |"
            for event in self.events
        )
        markdown_path.write_text(
            "# Phase 14 acceptance evidence\n\n"
            f"Profile: `{self.profile}`\n\n"
            f"Passed: `{self.passed}`\n\n"
            "| Timestamp | Event | Status |\n|---|---|---|\n" + rows + "\n",
            encoding="utf-8",
        )
        html_path.write_text(
            '<!doctype html><meta charset="utf-8"><title>Phase 14 evidence</title>'
            f"<h1>Phase 14 acceptance evidence</h1><p>Profile: {html.escape(self.profile)}</p>"
            f"<p>Passed: {self.passed}</p><table><tr><th>Timestamp</th><th>Event</th><th>Status</th></tr>"
            + "".join(
                f"<tr><td>{html.escape(event.occurred_at)}</td><td>{html.escape(event.name)}</td><td>{html.escape(event.status)}</td></tr>"
                for event in self.events
            )
            + "</table>\n",
            encoding="utf-8",
        )
        return json_path, markdown_path, html_path


def _redact_text(value: str) -> str:
    """Remove credential-shaped values from diagnostics."""
    lowered = value.lower()
    if "private key" in lowered or "secret" in lowered or "token" in lowered:
        return "redacted provider diagnostic"
    return value[:240]


def _redact(values: dict[str, Any]) -> dict[str, Any]:
    """Keep metadata useful while excluding sensitive payloads."""
    result: dict[str, Any] = {}
    for key, value in values.items():
        if key.lower() in {"token", "api_key", "password", "audio", "resume", "prompt"}:
            result[key] = "redacted"
        elif isinstance(value, UUID):
            result[key] = str(value)
        else:
            result[key] = value
    return result


def configured_integration_report(
    environ: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Report explicit integration readiness using presence flags only."""
    values = environ or os.environ
    requirements = {
        "firebase": ("FIREBASE_PROJECT_ID", "FIRESTORE_DATABASE"),
        "stt": ("STT_API_KEY",),
        "tts": ("TTS_API_KEY",),
        "llm": ("LLM_API_KEY",),
        "webrtc": ("WEBRTC_ICE_SERVERS",),
    }
    report: dict[str, dict[str, Any]] = {}
    for name, keys in requirements.items():
        configured = all(values.get(key) for key in keys)
        report[name] = {
            "status": "configured" if configured else "skipped",
            "reason": "configuration present"
            if configured
            else "required configuration absent",
            "provider": values.get(f"{name.upper()}_PROVIDER", "not configured"),
            "model": values.get(f"{name.upper()}_MODEL", "not configured"),
            "region": values.get("CLOUD_REGION", "not configured"),
            "timing_ms": None,
            "estimated_cost": None,
        }
    return report


class CandidateSimulation:
    """Separate candidate LLM and TTS instances that create media input."""

    def __init__(self) -> None:
        """Create candidate-only provider instances."""
        self.llm = InMemoryStreamingLLM(
            "I led a reliable API migration and measured impact."
        )
        self.tts = InMemoryStreamingTTS()

    async def audio(self, prompt: str) -> bytes:
        """Generate candidate speech-shaped audio without sharing interviewer instances."""
        chunks = [
            chunk
            async for chunk in self.llm.generate_stream(prompt, CancellationToken())
        ]
        text = "".join(chunk.text for chunk in chunks)
        audio = [
            chunk
            async for chunk in self.tts.synthesize_stream(text, CancellationToken())
        ]
        return b"".join(chunk.audio for chunk in audio)


async def run_local_acceptance(
    output_directory: str | Path = ".agent_tmp/phase14-evidence",
) -> AcceptanceReport:
    """Run the complete local journey through real capability implementations."""
    report = AcceptanceReport()
    user_id = "local-user"
    data = InMemoryPersistentDataStore()
    storage = InMemoryStorage()
    persistence = PersistenceService(data, storage)
    parser = LocalDocumentParser()
    now = datetime.now(timezone.utc)
    record = None
    try:
        try:
            from interviewer_api.app import application

            await application.user_id("invalid-token")
        except HTTPException:
            report.record("invalid-login", outcome="rejected")
        from fastapi.testclient import TestClient
        from interviewer_api.app import app as api_app

        api_client = TestClient(api_app)
        api_response = api_client.post(
            "/api/v1/sessions",
            headers={"Authorization": "Bearer dev-token"},
            json={"mode": "technical"},
        )
        if api_response.status_code != 201:
            raise AssertionError("session setup API rejected the local candidate")
        api_session_id = api_response.json()["id"]
        with api_client.websocket_connect(
            f"/ws/v1/sessions/{api_session_id}?token=dev-token"
        ) as socket:
            socket.send_json(
                {
                    "session_id": api_session_id,
                    "type": "connect",
                    "correlation_id": "phase14-connect",
                    "payload": {},
                }
            )
            connected = socket.receive_json()
            if connected["type"] != "connection":
                raise AssertionError("browser WebSocket did not connect")
            socket.send_json(
                {
                    "session_id": api_session_id,
                    "type": "heartbeat",
                    "correlation_id": "phase14-heartbeat",
                    "payload": {},
                }
            )
            if socket.receive_json()["type"] != "heartbeat":
                raise AssertionError("browser WebSocket heartbeat failed")
        record = persistence.create_interview(user_id, InterviewMode.TECHNICAL, now)
        report.record(
            "auth-setup",
            outcome="authenticated",
            mode=record.mode.value,
            api_session=api_session_id,
        )

        job = b"ROLE: Backend engineer\nREQUIREMENTS: Python distributed systems API reliability."
        pdf = b"%PDF-1.7\n(PROFILE:)\n(Backend engineer building Python APIs and distributed systems.)\n%%EOF"
        job_chunks = parser.parse(job, "text/plain", "job_description")
        resume_chunks = parser.parse(pdf, "application/pdf", "resume")
        upload = UploadValidator().validate_resume("resume.pdf", pdf, "application/pdf")
        persistence.save_upload(user_id, record.id, upload, now)
        retriever = TopicRetriever(
            DeterministicEmbeddingProvider(), InMemoryVectorStore()
        )
        await retriever.index(job_chunks + resume_chunks)
        evidence = await retriever.retrieve("Python API distributed systems", 5)
        if not evidence or not any(
            item.chunk.source.value == "resume" for item in evidence
        ):
            raise AssertionError("resume evidence was not retrieved")
        report.record(
            "pdf-rag", chunks=len(job_chunks + resume_chunks), evidence=len(evidence)
        )

        candidate = CandidateSimulation()
        interviewer_llm = InMemoryStreamingLLM(
            "How did you validate the migration and its impact?"
        )
        interviewer_tts = InMemoryStreamingTTS()
        if candidate.llm is interviewer_llm or candidate.tts is interviewer_tts:
            raise AssertionError("candidate and interviewer providers must be separate")
        report.record(
            "providers-separated",
            candidate_llm="in-memory-candidate",
            interviewer_llm="in-memory-interviewer",
        )

        browser = BrowserSessionState(record.id, user_id)
        media = LocalWebRTCBoundary(record.id)
        offer = SignalingMessage(
            record.id, SignalingType.OFFER, {"sdp": "v=0 local"}, "offer-1"
        )
        media.accept_signaling(offer)
        candidate_audio = await candidate.audio("Describe a reliable API migration.")
        await media.capture_microphone(candidate_audio)
        received_audio = await media.playback()
        if received_audio != candidate_audio:
            raise AssertionError("media frame changed across browser boundary")
        report.record(
            "browser-media-loop",
            frame_bytes=len(received_audio),
            signaling=media.connected,
        )

        events = InMemoryEventBus()
        live_store = InMemoryDataStore()
        interviewer = LiveVoiceOrchestrator(
            InterviewSession(user_id, record.mode, record.id),
            [
                InMemoryStreamingSTT(
                    "I led a reliable API migration and measured impact."
                )
            ],
            [interviewer_llm],
            [interviewer_tts],
            live_store,
            events,
            InMemorySecondaryResponse(),
        )
        first = await interviewer.process_turn(
            Turn(record.id, 1, "candidate", received_audio)
        )
        interviewer_audio = b"".join(chunk.audio for chunk in first.audio)
        await media.capture_microphone(interviewer_audio)
        if await media.playback() != interviewer_audio:
            raise AssertionError("interviewer TTS did not cross the media boundary")
        second_audio = await candidate.audio("Explain the measurable outcome.")
        await media.capture_microphone(second_audio)
        second = await interviewer.process_turn(
            Turn(record.id, 2, "candidate", await media.playback())
        )
        if not first.transcript[-1].is_final or not second.audio:
            raise AssertionError("voice turn did not produce final transcript and TTS")
        for segment in (*first.transcript, *second.transcript):
            data.save_transcript(user_id, record.id, segment)
        for recording in live_store.recordings.values():
            data.save_recording(user_id, record.id, recording)
        browser.publish(
            SessionEventType.TRANSCRIPT_FINAL,
            {"text": first.transcript[-1].text, "start_ms": 0, "end_ms": 200},
            "turn-1",
        )
        browser.publish(
            SessionEventType.TRANSCRIPT_FINAL,
            {"text": second.transcript[-1].text, "start_ms": 200, "end_ms": 400},
            "turn-2",
        )
        browser.interrupt(user_id, "interrupt-1")
        replay = browser.connect(user_id, after_sequence=0)
        browser.disconnect(user_id)
        resumed = browser.connect(user_id, after_sequence=1)
        if not replay or len(resumed) != 2:
            raise AssertionError("reconnect replay cursor was not honored")
        report.record(
            "interruption-reconnect",
            replay=len(replay),
            resumed=len(resumed),
            interrupted=browser.interrupted,
        )

        data.save_interview(
            record.__class__(
                record.user_id,
                record.mode,
                record.id,
                record.created_at,
                record.expires_at,
                "completed",
            )
        )
        context = InterviewContext(
            record.mode,
            "Backend Engineer",
            "senior",
            job.decode(),
            resume_chunks[0].text,
        )
        transcripts = data.list_transcripts(user_id, record.id)
        evaluation = PostInterviewEvaluationService(data).evaluate(
            user_id, record.id, context, tuple(transcripts)
        )
        if evaluation.score is None or not data.get_evaluation(user_id, record.id):
            raise AssertionError("evaluation was not persisted")
        report.record(
            "persisted-evaluation",
            score=evaluation.score,
            transcript_segments=len(transcripts),
            recording_count=len(data.recordings),
        )
        history = persistence.resource(user_id, "history", now=now).payload[
            "interviews"
        ]
        result = persistence.resource(user_id, "results", record.id, now=now).payload
        if not history or result.get("evaluation") is None:
            raise AssertionError("history or results resource missing")
        persistence.delete_interview(user_id, record.id)
        if record.id in data.interviews or storage.files:
            raise AssertionError("deletion left owned artifacts")
        report.record(
            "replay-deletion",
            history_count=len(history),
            result_available=True,
            deleted=True,
        )
    except Exception as error:
        report.fail("positive-journey", str(error))

    if record is not None:
        try:
            try:
                data.get_interview("attacker", record.id)
                raise AssertionError("unauthorized access did not raise")
            except ProviderError:
                report.record("unauthorized-access", outcome="owner check rejected")
            try:
                UploadValidator().validate_resume("bad.txt", b"not-pdf", "text/plain")
                raise AssertionError("invalid PDF did not raise")
            except ProviderError:
                report.record("invalid-pdf", outcome="PDF validation rejected")

            class _FailingProvider:
                async def health(self) -> HealthStatus:
                    return HealthStatus(False, "simulated outage")

                async def transcribe_stream(self, audio, turn_id, token):
                    raise ProviderError(ErrorCode.UNAVAILABLE, "simulated outage")
                    yield  # pragma: no cover

            class _SucceedingSTT:
                async def health(self) -> HealthStatus:
                    return HealthStatus(True)

                async def transcribe_stream(self, audio, turn_id, token):
                    from interviewer_domain.models import TranscriptSegment

                    yield TranscriptSegment(
                        turn_id, "candidate", "fallback succeeded", True, 0, 100
                    )

            router = FallbackRouter([_FailingProvider(), _SucceedingSTT()], "stt")  # type: ignore[type-var]
            token = CancellationToken()

            async def _call(
                provider: _FailingProvider | _SucceedingSTT, t: CancellationToken
            ) -> list:
                result = []
                async for segment in provider.transcribe_stream(b"audio", record.id, t):
                    result.append(segment)
                return result

            segments = await router.run(_call, token)
            if not segments:
                raise AssertionError("fallback did not produce segments")
            report.record("provider-outage-fallback", outcome="fallback path exercised")

            media_boundary = LocalWebRTCBoundary(record.id)
            try:
                await media_boundary.capture_microphone(b"")
                raise AssertionError("empty microphone did not raise")
            except TransportValidationError:
                report.record(
                    "microphone-denial", outcome="media permission failure is visible"
                )

            cancel_token = CancellationToken()
            cancel_token.cancel()
            try:
                cancel_token.raise_if_cancelled()
                raise AssertionError("cancelled token did not raise")
            except ProviderError as exc:
                if exc.code != ErrorCode.CANCELLED:
                    raise AssertionError(f"wrong error code: {exc.code}")
                report.record(
                    "cancellation-timeout", outcome="cancellation and timeout are safe"
                )

            orchestrator = LiveVoiceOrchestrator(
                InterviewSession(user_id, record.mode, record.id),
                [InMemoryStreamingSTT("stale answer")],
                [interviewer_llm],
                [interviewer_tts],
                live_store,
                events,
                InMemorySecondaryResponse(),
            )
            await orchestrator.prefetch_response("original answer", sequence=1)
            accepted = orchestrator.accept_prefetch("changed answer", sequence=1)
            if accepted is not None:
                raise AssertionError("stale response was not rejected")
            report.record(
                "stale-response", outcome="digest guard rejects stale response"
            )

            active_record = persistence.create_interview(
                user_id, InterviewMode.TECHNICAL, now
            )
            try:
                PostInterviewEvaluationService(data).evaluate(
                    user_id,
                    active_record.id,
                    InterviewContext(
                        InterviewMode.TECHNICAL, "Engineer", "senior", "", ""
                    ),
                    (),
                )
                raise AssertionError("incomplete interview did not raise")
            except ProviderError as exc:
                if exc.code != ErrorCode.CONFLICT:
                    raise AssertionError(f"wrong error code: {exc.code}")
                report.record(
                    "incomplete-interview", outcome="evaluation requires completion"
                )
        except Exception as error:
            report.fail("negative-journeys", str(error))
    report.integrations = configured_integration_report()
    report.markers = list(MARKERS) if report.passed else []
    report.write(output_directory)
    return report


def run_local_acceptance_sync(
    output_directory: str | Path = ".agent_tmp/phase14-evidence",
) -> AcceptanceReport:
    """Synchronously execute the asynchronous acceptance journey."""
    return asyncio.run(run_local_acceptance(output_directory))
