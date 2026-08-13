"""FastAPI composition root for the deterministic local interview service."""

from __future__ import annotations

from dataclasses import replace
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from interviewer_domain.adapters.integrations import IntegrationSkipped, SyncOpenRouterHTTPTransport
from interviewer_domain.capabilities.contracts import (
    AuthProvider,
    LLMProvider,
    StreamingLLMProvider,
    StreamingSTTProvider,
    StreamingTTSProvider,
    STTProvider,
    TTSProvider,
)
from interviewer_domain.configuration import (
    ProviderReadinessChecker,
    RuntimeSettings,
    compose_providers,
    validate_beta_composition,
)
from interviewer_domain.contracts import ErrorCode, ProviderError
from interviewer_domain.models import InterviewMode, InterviewSession, Turn, TranscriptSegment, Recording, LifecycleEvent
from interviewer_domain.live_voice import LiveVoiceOrchestrator
from interviewer_domain.evaluation import InterviewContext, PostInterviewEvaluationService
from interviewer_domain.contracts import CancellationToken, StreamAudioChunk, StreamTextChunk
from interviewer_domain.adapters.evaluator import OpenRouterEvaluator
from interviewer_domain.persistence import (
    FirebaseAuthAdapter,
    FirestoreDataStore,
    PersistentDataStore,
    PersistentStorageProvider,
    S3CompatibleStorage,
    FixedWindowRateLimiter,
    InMemoryAuthProvider,
    InMemoryPersistentDataStore,
    LocalFilesystemStorage,
    PersistenceService,
    UserIdentity,
)
from interviewer_domain.provider_integration import (
    FirebaseAdminAuthBackend,
    FirebaseStorageBackend,
    FirestoreGoogleBackend,
)
from interviewer_domain.transport import (
    BrowserSessionState,
    CreateSessionRequest,
    LocalWebRTCBoundary,
    RestResourceCatalog,
    SessionCommand,
    SessionCommandType,
    SessionEventType,
    SignalingMessage,
    SignalingType,
    TransportValidationError,
)

APP_VERSION = "0.11.0"


class _SessionDataStore:
    """Adapt owner-scoped persistence to the live voice DataStore contract."""

    def __init__(self, data: PersistentDataStore, user_id: str, session_id: UUID) -> None:
        self.data = data
        self.user_id = user_id
        self.session_id = session_id

    def link_turn_session(self, turn_id: UUID, session_id: UUID) -> None:
        """Retain the association through normalized transcript records."""

    def save_transcript(self, segment: TranscriptSegment) -> None:
        """Persist a live transcript segment under its owning interview."""
        self.data.save_transcript(self.user_id, self.session_id, segment)

    def list_transcript(self, session_id: UUID) -> list[TranscriptSegment]:
        """Return all persisted transcript segments for this session."""
        return self.data.list_transcripts(self.user_id, session_id)

    def save_recording(self, recording: Recording) -> None:
        """Persist recording metadata under its owning interview."""
        self.data.save_recording(self.user_id, self.session_id, recording)


class _SessionEventBus:
    """Translate live-domain events into the browser session event vocabulary."""

    _EVENTS = {
        "transcript.partial": SessionEventType.TRANSCRIPT_PARTIAL,
        "transcript.final": SessionEventType.TRANSCRIPT_FINAL,
        "playback.interrupted": SessionEventType.PLAYBACK_STOPPED,
        "provider.fallback": SessionEventType.PROVIDER_STATUS,
        "live.turn.started": SessionEventType.PROVIDER_STATUS,
        "live.turn.completed": SessionEventType.PROVIDER_STATUS,
        "live.latency": SessionEventType.PROVIDER_STATUS,
    }

    def __init__(self, state: BrowserSessionState) -> None:
        self.state = state

    async def publish(self, event: LifecycleEvent) -> None:
        """Publish a normalized event without exposing provider internals."""
        event_type = self._EVENTS.get(event.name, SessionEventType.ERROR)
        self.state.publish(event_type, dict(event.payload), event.correlation_id)


class _BatchStreamingSTT:
    """Expose a normalized batch STT provider through the streaming seam."""

    def __init__(self, provider: STTProvider) -> None:
        self.provider = provider

    async def _stream(self, audio: bytes, turn_id: UUID, token: CancellationToken) -> AsyncIterator[TranscriptSegment]:
        """Yield the provider's final transcript as one streaming segment."""
        yield await self.provider.transcribe(audio, turn_id, token)

    def transcribe_stream(self, audio: bytes, turn_id: UUID, token: CancellationToken) -> AsyncIterator[TranscriptSegment]:
        """Return an asynchronous transcript stream."""
        return self._stream(audio, turn_id, token)


class _BatchStreamingLLM:
    """Expose a normalized batch LLM provider through the streaming seam."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def _stream(self, prompt: str, token: CancellationToken) -> AsyncIterator[StreamTextChunk]:
        """Yield the complete response as an ordered text chunk."""
        yield StreamTextChunk(0, await self.provider.generate(prompt, token), True)

    def generate_stream(self, prompt: str, token: CancellationToken) -> AsyncIterator[StreamTextChunk]:
        """Return an asynchronous response stream."""
        return self._stream(prompt, token)


class _BatchStreamingTTS:
    """Expose a normalized batch TTS provider through the streaming seam."""

    def __init__(self, provider: TTSProvider) -> None:
        self.provider = provider

    async def _stream(self, text: str, token: CancellationToken) -> AsyncIterator[StreamAudioChunk]:
        """Yield provider audio as one browser-schedulable chunk."""
        audio = await self.provider.synthesize(text, token)
        yield StreamAudioChunk(0, audio, 0, max(1, len(audio)))

    def synthesize_stream(self, text: str, token: CancellationToken) -> AsyncIterator[StreamAudioChunk]:
        """Return an asynchronous audio stream."""
        return self._stream(text, token)


def _stt_chain(chain: tuple[STTProvider, ...]) -> tuple[StreamingSTTProvider, ...]:
    """Wrap configured batch STT providers while retaining fallback ordering."""
    return tuple(_BatchStreamingSTT(provider) for provider in chain)


def _llm_chain(chain: tuple[LLMProvider, ...]) -> tuple[StreamingLLMProvider, ...]:
    """Wrap configured batch LLM providers while retaining fallback ordering."""
    return tuple(_BatchStreamingLLM(provider) for provider in chain)


def _tts_chain(chain: tuple[TTSProvider, ...]) -> tuple[StreamingTTSProvider, ...]:
    """Wrap configured batch TTS providers while retaining fallback ordering."""
    return tuple(_BatchStreamingTTS(provider) for provider in chain)
settings = RuntimeSettings.from_env()
runtime_providers = compose_providers(settings)


class CreateInterviewRequest(BaseModel):
    """Validated interview setup payload."""

    mode: str = Field(pattern="^(recruiter|technical)$")


class InterviewApplication:
    """Own injected local capabilities and expose application use cases."""

    def __init__(self) -> None:
        """Create the local composition or the explicitly configured live composition."""
        self.data: PersistentDataStore
        self.auth: AuthProvider
        if settings.profile.value == "production":
            validate_beta_composition(settings)
            auth_backend = FirebaseAdminAuthBackend(
                settings.firebase_credentials_path, settings.firebase_project_id
            )
            firestore_backend = FirestoreGoogleBackend(
                settings.firebase_project_id or "", settings.firestore_database or "(default)"
            )
            self.data = FirestoreDataStore(firestore_backend)
            storage: PersistentStorageProvider
            if settings.storage_backend == "local":
                storage = LocalFilesystemStorage(settings.storage_path)
            elif settings.storage_backend == "s3":
                from interviewer_domain.adapters.integrations import Boto3ObjectBackend

                try:
                    storage = S3CompatibleStorage(Boto3ObjectBackend(settings.storage_bucket or ""))
                except IntegrationSkipped as exc:
                    raise RuntimeError(f"S3 storage backend requires boto3: {exc}") from exc
            elif settings.storage_backend == "gcs":
                assert settings.storage_bucket is not None
                storage = S3CompatibleStorage(FirebaseStorageBackend(settings.storage_bucket))
            else:
                raise RuntimeError(f"unsupported STORAGE_BACKEND: {settings.storage_backend}")
            self.persistence = PersistenceService(
                self.data, storage, settings.retention_days
            )
            self.auth = FirebaseAuthAdapter(auth_backend)
        else:
            self.data = InMemoryPersistentDataStore()
            self.persistence = PersistenceService(
                self.data, LocalFilesystemStorage(settings.storage_path), settings.retention_days
            )
            self.auth = InMemoryAuthProvider({"dev-token": UserIdentity("local-user")})
        self.rate_limiter = FixedWindowRateLimiter(
            limit=settings.rate_limit, window_seconds=settings.rate_window_seconds
        )
        self.browser_sessions: dict[UUID, BrowserSessionState] = {}
        self.media_boundaries: dict[UUID, LocalWebRTCBoundary] = {}
        self.voice_sessions: dict[UUID, LiveVoiceOrchestrator] = {}
        self.evaluators: dict[UUID, PostInterviewEvaluationService] = {}

    async def user_id(self, token: str) -> str:
        """Resolve a bearer token without exposing token details."""
        try:
            return await self.auth.validate(token)
        except ProviderError as error:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "authentication required"
            ) from error


application = InterviewApplication()
app = FastAPI(title="AI Mock Interview API", version=APP_VERSION)


async def current_user(authorization: Annotated[str | None, Header()] = None) -> str:
    """Require the documented local bearer token boundary."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    user = await application.user_id(authorization.removeprefix("Bearer ").strip())
    if not application.rate_limiter.allow(user, datetime.now(timezone.utc)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate limit exceeded")
    return user


def _safe_error(error: ProviderError) -> HTTPException:
    """Map domain errors to stable HTTP responses without internal details."""
    code = {
        ErrorCode.INVALID_REQUEST: 400,
        ErrorCode.CONFLICT: 409,
        ErrorCode.UNAVAILABLE: 404,
    }.get(error.code, 500)
    return HTTPException(code, "request cannot be completed")


@app.get("/healthz")
async def health() -> dict[str, str]:
    """Return a liveness response without credentials or domain data."""
    return {"status": "ok"}


@app.get("/api/v1/health")
async def api_health() -> dict[str, str]:
    """Return the versioned health response."""
    return {"status": "ok", "version": APP_VERSION}


@app.get("/api/v1/readiness")
async def readiness() -> dict[str, object]:
    """Return redacted runtime profile and normalized capability readiness."""
    reports = await ProviderReadinessChecker(
        runtime_providers, settings.profile.value == "production"
    ).check()
    return {
        "profile": settings.profile.value,
        "diagnostics": settings.diagnostics(),
        "capabilities": {
            report.capability: {
                "healthy": report.healthy,
                "providers": [descriptor.name for descriptor in report.descriptors],
                "statuses": [hs.healthy for hs in report.statuses],
            }
            for report in reports
        },
    }


@app.get("/api/v1/version")
async def version() -> dict[str, str]:
    """Return the running API version."""
    return {"version": APP_VERSION}


@app.post("/api/v1/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: CreateInterviewRequest, user_id: Annotated[str, Depends(current_user)]
) -> dict[str, object]:
    """Create an owned interview resource through the persistence service."""
    record = application.persistence.create_interview(
        user_id, InterviewMode(payload.mode), datetime.now(timezone.utc)
    )
    response = RestResourceCatalog.create_session(
        CreateSessionRequest(user_id, payload.mode), record.id
    )
    state = BrowserSessionState(record.id, user_id)
    application.browser_sessions[record.id] = state
    application.media_boundaries[record.id] = LocalWebRTCBoundary(record.id)
    session = InterviewSession(user_id, record.mode, record.id)
    voice_store = _SessionDataStore(application.data, user_id, record.id)
    application.voice_sessions[record.id] = LiveVoiceOrchestrator(
        session,
        _stt_chain(cast(tuple[STTProvider, ...], runtime_providers.stt)),
        _llm_chain(cast(tuple[LLMProvider, ...], runtime_providers.llm)),
        _tts_chain(cast(tuple[TTSProvider, ...], runtime_providers.tts)),
        voice_store,
        _SessionEventBus(state),
    )
    evaluator = None
    if settings.profile.value == "production" and settings.llm_provider == "openrouter":
        evaluator = OpenRouterEvaluator(SyncOpenRouterHTTPTransport(), settings.llm_api_key or "", settings.llm_model)
    application.evaluators[record.id] = PostInterviewEvaluationService(application.data, evaluator)
    result: dict[str, object] = {
        key: value for key, value in response.to_dict().items()
    }
    result.update({"status": record.status})
    return result


@app.get("/api/v1/history")
async def history(user_id: Annotated[str, Depends(current_user)]) -> dict[str, object]:
    """Return only non-expired interviews owned by the authenticated user."""
    return application.persistence.resource(user_id, "history").to_dict()


@app.get("/api/v1/sessions/{interview_id}/{view}")
async def resource(
    interview_id: UUID, view: str, user_id: Annotated[str, Depends(current_user)]
) -> dict[str, object]:
    """Return one authorized setup, active, replay, transcript, or results view."""
    if view not in {"setup", "active", "replay", "transcript", "results"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "resource not found")
    try:
        return application.persistence.resource(user_id, view, interview_id).to_dict()
    except ProviderError as error:
        raise _safe_error(error) from error


@app.post("/api/v1/sessions/{interview_id}/complete")
async def complete(
    interview_id: UUID, user_id: Annotated[str, Depends(current_user)]
) -> dict[str, str]:
    """Complete an owned interview using the real persistence record."""
    try:
        record = application.data.get_interview(user_id, interview_id)
        application.data.save_interview(replace(record, status="completed"))
        transcript = tuple(application.data.list_transcripts(user_id, interview_id))
        evaluator = application.evaluators.get(interview_id)
        if evaluator is None:
            raise HTTPException(status_code=404, detail="evaluator not found for session")
        evaluation = evaluator.evaluate(
            user_id, interview_id,
            InterviewContext(record.mode, "the supplied role", "the supplied seniority"),
            transcript,
        )
        return {"id": str(interview_id), "status": "completed", "score": str(evaluation.score)}
    except ProviderError as error:
        raise _safe_error(error) from error


async def _websocket_user(websocket: WebSocket) -> str | None:
    """Resolve the development bearer token supplied to a browser socket."""
    token = websocket.query_params.get("token", "")
    try:
        return await application.auth.validate(token)
    except ProviderError:
        return None


@app.websocket("/ws/v1/sessions/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: UUID) -> None:
    """Serve authenticated control events while keeping media off the socket."""
    user_id = await _websocket_user(websocket)
    state = application.browser_sessions.get(session_id)
    if user_id is None or state is None:
        await websocket.accept()
        await websocket.close(code=4401, reason="authentication required")
        return
    try:
        state.authorize(user_id)
    except TransportValidationError:
        await websocket.accept()
        await websocket.close(code=4403, reason="session access denied")
        return
    await websocket.accept()
    correlation_id = f"ws-{session_id}"
    try:
        while True:
            raw = await websocket.receive_json()
            command = SessionCommand.from_dict(raw)
            if command.session_id != session_id:
                raise TransportValidationError("command session does not match socket")
            if command.command_type == SessionCommandType.CONNECT:
                events = state.connect(user_id, command.acknowledged_sequence)
                events.append(state.publish(SessionEventType.CONNECTION, {"state": "connected"}, command.correlation_id))
                for event in events:
                    await websocket.send_json(event.to_dict())
            elif command.command_type == SessionCommandType.ACK:
                state.acknowledge(user_id, command.acknowledged_sequence)
            elif command.command_type == SessionCommandType.HEARTBEAT:
                event = state.publish(SessionEventType.HEARTBEAT, {"state": "alive"}, command.correlation_id)
                await websocket.send_json(event.to_dict())
            elif command.command_type == SessionCommandType.CANCEL:
                event = state.cancel(user_id, command.correlation_id)
                await websocket.send_json(event.to_dict())
            elif command.command_type == SessionCommandType.INTERRUPT:
                event = state.interrupt(user_id, command.correlation_id)
                await websocket.send_json(event.to_dict())
            elif command.command_type == SessionCommandType.TURN_START:
                audio = await application.media_boundaries[session_id].playback()
                if not audio:
                    raise TransportValidationError("microphone media is required before turn.start")
                result = await application.voice_sessions[session_id].process_turn(
                    Turn(session_id, int(command.payload.get("sequence", 1)), "candidate", audio)
                )
                if not result.interrupted:
                    await websocket.send_json(state.publish(
                        SessionEventType.PLAYBACK_STARTED,
                        {"text": result.response, "audio_chunks": len(result.audio), "latency_ms": result.latency_ms},
                        command.correlation_id,
                    ).to_dict())
            elif command.command_type == SessionCommandType.SIGNALING:
                message = SignalingMessage(
                    session_id,
                    SignalingType(str(command.payload.get("type", ""))),
                    dict(command.payload.get("payload", {})),
                    command.correlation_id,
                )
                application.media_boundaries[session_id].accept_signaling(message)
                event = state.publish(SessionEventType.CONNECTION, {"state": "signaling-received", "type": message.message_type.value}, command.correlation_id)
                await websocket.send_json(event.to_dict())
            elif command.command_type == SessionCommandType.CLOSE:
                state.disconnect(user_id)
                await websocket.close(code=1000, reason="client closed")
                return
            else:
                raise TransportValidationError("unsupported session command")
    except WebSocketDisconnect:
        state.disconnect(user_id)
    except (TransportValidationError, KeyError, ValueError, ProviderError) as error:
        event = state.publish(SessionEventType.ERROR, {"code": "invalid_control", "message": str(error)}, correlation_id)
        await websocket.send_json(event.to_dict())
        await websocket.close(code=1003, reason="invalid control payload")


@app.websocket("/ws/v1/sessions/{session_id}/media")
async def media_websocket(websocket: WebSocket, session_id: UUID) -> None:
    """Buffer authenticated binary microphone frames on the media boundary."""
    user_id = await _websocket_user(websocket)
    state = application.browser_sessions.get(session_id)
    if user_id is None or state is None:
        await websocket.accept()
        await websocket.close(code=4401, reason="authentication required")
        return
    try:
        state.authorize(user_id)
    except TransportValidationError:
        await websocket.accept()
        await websocket.close(code=4403, reason="session access denied")
        return
    await websocket.accept()
    try:
        while True:
            frame = await websocket.receive_bytes()
            await application.media_boundaries[session_id].capture_microphone(frame)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/v1/sessions/{session_id}/signaling")
async def signaling_websocket(websocket: WebSocket, session_id: UUID) -> None:
    """Accept authenticated offer, answer, and ICE signaling only."""
    user_id = await _websocket_user(websocket)
    state = application.browser_sessions.get(session_id)
    if user_id is None or state is None:
        await websocket.accept()
        await websocket.close(code=4401, reason="authentication required")
        return
    try:
        state.authorize(user_id)
    except TransportValidationError:
        await websocket.accept()
        await websocket.close(code=4403, reason="session access denied")
        return
    try:
        await websocket.accept()
        raw = await websocket.receive_json()
        message = SignalingMessage(
            session_id,
            SignalingType(str(raw["type"])),
            dict(raw.get("payload", {})),
            str(raw["correlation_id"]),
        )
        application.media_boundaries[session_id].accept_signaling(message)
        await websocket.send_json({"ok": True, "type": message.message_type.value, "session_id": str(session_id)})
        await websocket.close(code=1000)
    except (TransportValidationError, KeyError, ValueError):
        await websocket.close(code=1003, reason="invalid signaling")
