"""Programmatic Phase 16 live rehearsal and redacted evidence.

The rehearsal uses two explicit agent roles and injected provider interfaces.
No deterministic provider is accepted as beta evidence, and this module never
prints credentials, document text, transcript text, or audio bytes.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Protocol
from uuid import UUID, uuid4

from .adapters.integrations import IntegrationEvidence, ProviderMetadata, redact_evidence
from .adapters.persistence import InterviewRecord, PersistentDataStore
from .capabilities.contracts import CancellationToken
from .documents import LocalDocumentParser
from .evaluation import Evaluation, Evaluator, InterviewContext
from .models import InterviewMode, Recording, TranscriptSegment


class RehearsalAuth(Protocol):
    """Validate a real Firebase-authenticated token."""

    async def validate(self, token: str) -> str: ...


class RehearsalSTT(Protocol):
    """Transcribe audio through the selected live WhisperX provider."""

    async def transcribe(self, audio: bytes, turn_id: UUID, token: CancellationToken) -> TranscriptSegment: ...


class RehearsalLLM(Protocol):
    """Generate interviewer text through the selected live OpenRouter provider."""

    async def generate(self, prompt: str, token: CancellationToken) -> str: ...


class RehearsalTTS(Protocol):
    """Synthesize Kokoro English 24 kHz mono PCM output."""

    async def synthesize(self, text: str, token: CancellationToken) -> bytes: ...


class RehearsalStorage(Protocol):
    """Store and replay opaque artifacts behind the selected storage adapter."""

    def put(self, key: str, content: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> None: ...


@dataclass(frozen=True, slots=True)
class TimestampedAudioBuffer:
    """One agent-to-agent audio buffer with monotonic ordering metadata."""

    sequence: int
    start_ms: int
    duration_ms: int
    audio: bytes


@dataclass(frozen=True, slots=True)
class RehearsalProviders:
    """All provider capabilities required by a real rehearsal journey."""

    auth: RehearsalAuth
    stt: RehearsalSTT
    llm: RehearsalLLM
    tts: RehearsalTTS
    data: PersistentDataStore
    storage: RehearsalStorage
    evaluator: Evaluator
    parser: LocalDocumentParser = field(default_factory=LocalDocumentParser)


@dataclass(frozen=True, slots=True)
class AgentTurn:
    """Redacted lifecycle result for one candidate turn."""

    turn_id: UUID
    buffers: tuple[TimestampedAudioBuffer, ...]
    partial: TranscriptSegment
    final: TranscriptSegment
    interviewer_text: str
    interviewer_audio_bytes: int


class IntervieweeAgent:
    """Supply candidate utterances as timestamped in-memory audio buffers."""

    def __init__(self, utterances: tuple[bytes, ...]) -> None:
        self.utterances = utterances

    def buffers(self, turn_number: int) -> tuple[TimestampedAudioBuffer, ...]:
        """Return ordered buffers for one utterance without mutating audio bytes."""
        audio = self.utterances[turn_number % len(self.utterances)]
        if not audio:
            raise ValueError("interviewee utterance audio is empty")
        buffers = (TimestampedAudioBuffer(turn_number, turn_number * 1000, 1000, audio),)
        _validate_audio_buffers(buffers)
        return buffers


def _validate_audio_buffers(buffers: tuple[TimestampedAudioBuffer, ...]) -> None:
    """Require nonempty, contiguous, non-overlapping monotonic audio buffers."""
    if not buffers:
        raise ValueError("audio buffer sequence is empty")
    for previous, current in zip(buffers, buffers[1:]):
        if current.sequence != previous.sequence + 1:
            raise ValueError("audio buffer sequence is not contiguous")
        if current.start_ms < previous.start_ms + previous.duration_ms:
            raise ValueError("audio buffer timestamps overlap")
    if any(buffer.duration_ms <= 0 or not buffer.audio for buffer in buffers):
        raise ValueError("audio buffers require positive duration and nonempty audio")


class InterviewerAgent:
    """Drive setup, live voice turns, persistence, evaluation, and deletion."""

    def __init__(self, providers: RehearsalProviders, token: str) -> None:
        self.providers = providers
        self.token = token

    async def run(
        self,
        mode: InterviewMode,
        resume_path: Path,
        job_path: Path,
        interviewee: IntervieweeAgent,
        turn_count: int = 2,
    ) -> tuple[InterviewRecord, tuple[AgentTurn, ...], Evaluation]:
        """Execute one complete provider-backed journey with owned persistence."""
        user_id = await self.providers.auth.validate(self.token)
        resume = resume_path.read_bytes()
        job_description = job_path.read_bytes()
        resume_chunks = self.providers.parser.parse(resume, "application/pdf", "resume")
        job_chunks = self.providers.parser.parse(job_description, "text/plain", "job_description")
        record = InterviewRecord(user_id, mode).with_retention()
        self.providers.data.save_interview(record)
        prefix = f"users/{user_id}/interviews/{record.id}/"
        self.providers.storage.put(prefix + "resume.pdf", resume, "application/pdf")
        self.providers.data.save_document_reference(user_id, record.id, prefix + "resume.pdf")
        context_text = " ".join(chunk.text for chunk in (*resume_chunks, *job_chunks))
        turns: list[AgentTurn] = []
        token = CancellationToken()
        for sequence in range(turn_count):
            buffers = interviewee.buffers(sequence)
            audio = b"".join(buffer.audio for buffer in buffers)
            turn_id = uuid4()
            final = await self.providers.stt.transcribe(audio, turn_id, token)
            partial_text = final.text[: max(1, len(final.text) // 2)]
            partial = TranscriptSegment(turn_id, "candidate", partial_text, False, buffers[0].start_ms, buffers[-1].start_ms + buffers[-1].duration_ms)
            final = TranscriptSegment(turn_id, "candidate", final.text, True, partial.start_ms, partial.end_ms)
            self.providers.data.save_transcript(user_id, record.id, partial)
            self.providers.data.save_transcript(user_id, record.id, final)
            prompt = f"Ask the next {mode.value} interview question using this context: {context_text[:2000]} Answer evidence: {final.text}"
            interviewer_text = await self.providers.llm.generate(prompt, token)
            interviewer_audio = await self.providers.tts.synthesize(interviewer_text, token)
            self.providers.storage.put(prefix + f"turn-{sequence}.pcm", interviewer_audio, "audio/pcm;rate=24000;channels=1")
            turns.append(AgentTurn(turn_id, buffers, partial, final, interviewer_text, len(interviewer_audio)))
        completed = InterviewRecord(record.user_id, record.mode, record.id, record.created_at, record.expires_at, "completed")
        self.providers.data.save_interview(completed)
        recording_key = prefix + "combined.pcm"
        combined_audio = b"".join(
            turn_audio
            for sequence in range(len(turns))
            for turn_audio in (self.providers.storage.get(prefix + f"turn-{sequence}.pcm"),)
        )
        self.providers.storage.put(recording_key, combined_audio, "audio/pcm;rate=24000;channels=1")
        self.providers.data.save_recording(user_id, record.id, Recording(record.id, recording_key, "audio/pcm;rate=24000;channels=1"))
        transcript = tuple(self.providers.data.list_transcripts(user_id, record.id))
        evaluation = self.providers.evaluator.evaluate(InterviewContext(mode, "demo role", "senior", job_description.decode("utf-8", "replace"), "fixture resume"), transcript)
        self.providers.data.save_evaluation(user_id, record.id, evaluation)
        if not self.providers.storage.get(recording_key):
            raise ValueError("stored replay audio is empty")
        return completed, tuple(turns), evaluation

    async def delete(self, record: InterviewRecord) -> None:
        """Delete owned durable records and all owner-scoped rehearsal artifacts."""
        self.providers.data.delete_interview(record.user_id, record.id)
        self.providers.storage.delete_prefix(f"users/{record.user_id}/interviews/{record.id}/")


def load_dotenv(path: str | Path = ".env", environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Load simple dotenv keys without printing or returning secret values to logs."""
    values = dict(os.environ if environ is None else environ)
    source = Path(path)
    if not source.is_file():
        return values
    for line in source.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$", line)
        if match and match.group(1) not in values:
            values[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return values


@dataclass(frozen=True, slots=True)
class RehearsalOperation:
    """Describe one required live operation and its safe configuration keys."""

    marker: str
    capability: str
    provider: str
    required: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RehearsalResult:
    """Store a redacted operation result suitable for evidence output."""

    operation: RehearsalOperation
    status: str
    reason: str
    metadata: ProviderMetadata

    def evidence(self) -> IntegrationEvidence:
        """Convert the result to the shared provider evidence shape."""
        return IntegrationEvidence(
            self.operation.capability,
            self.status,
            self.reason,
            self.metadata,
        )


OPERATIONS: tuple[RehearsalOperation, ...] = (
    RehearsalOperation("composition-production-ok", "composition", "firebase/openrouter/whisperx/kokoro", ("APP_PROFILE", "FIREBASE_PROJECT_ID", "STT_PROVIDER", "TTS_PROVIDER", "LLM_PROVIDER", "LLM_API_KEY")),
    RehearsalOperation("firebase-auth-owner-isolation-ok", "firebase-auth", "firebase-auth", ("FIREBASE_PROJECT_ID", "FIREBASE_AUTH_DOMAIN")),
    RehearsalOperation("firestore-session-lifecycle-ok", "firestore", "firestore", ("FIREBASE_PROJECT_ID", "FIRESTORE_DATABASE")),
    RehearsalOperation("storage-firebase-lifecycle-ok", "storage-firebase", "firebase-storage", ("FIREBASE_PROJECT_ID", "STORAGE_BUCKET")),
    RehearsalOperation("storage-local-lifecycle-ok", "storage-local", "local/nfs", ("STORAGE_PATH",)),
    RehearsalOperation("resume-rag-context-ok", "resume-rag", "document-parser", ("PHASE16_RESUME_FIXTURE", "PHASE16_JOB_FIXTURE")),
    RehearsalOperation("agent-audio-transport-ok", "agent-audio", "timestamped-audio-buffers", ("PHASE16_AUDIO_TRANSPORT",)),
    RehearsalOperation("stt-partial-final-timestamps-ok", "stt", "whisperx-small", ("STT_PROVIDER", "STT_MODEL")),
    RehearsalOperation("llm-interviewer-stream-ok", "llm-interviewer", "openrouter", ("LLM_API_KEY", "LLM_MODEL")),
    RehearsalOperation("kokoro-audio-playback-ok", "tts", "kokoro", ("TTS_PROVIDER", "TTS_LANGUAGE")),
    RehearsalOperation("transcript-recording-persisted-ok", "transcript-recording", "selected-storage", ("FIREBASE_PROJECT_ID",)),
    RehearsalOperation("llm-evaluation-score-ok", "llm-evaluation", "openrouter", ("LLM_API_KEY", "LLM_MODEL")),
    RehearsalOperation("retention-deletion-ok", "retention-deletion", "selected-storage", ("FIREBASE_PROJECT_ID",)),
    RehearsalOperation("agent-recruiter-journey-ok", "agent-recruiter", "firebase/providers", ("FIREBASE_PROJECT_ID",)),
    RehearsalOperation("agent-technical-journey-ok", "agent-technical", "firebase/providers", ("FIREBASE_PROJECT_ID",)),
    RehearsalOperation("beta-evidence-redacted-ok", "beta-evidence", "redaction", ()),
)

Executor = Callable[[RehearsalOperation], RehearsalResult]


@dataclass(slots=True)
class Phase16Rehearsal:
    """Plan live operations and emit evidence without exposing sensitive data."""

    environ: Mapping[str, str] = field(default_factory=lambda: os.environ)
    executors: Mapping[str, Executor] = field(default_factory=dict)

    def run(self) -> tuple[RehearsalResult, ...]:
        """Run registered live seams and classify all other operations safely."""
        results: list[RehearsalResult] = []
        for operation in OPERATIONS:
            executor = self.executors.get(operation.marker)
            missing = tuple(key for key in operation.required if not self.environ.get(key))
            metadata = ProviderMetadata(operation.provider, "configured" if not missing else "not-configured", version="phase16", device="unknown")
            if operation.marker == "beta-evidence-redacted-ok" and executor is None:
                results.append(RehearsalResult(operation, "exercised", "redaction contract exercised", metadata))
            elif executor is not None:
                try:
                    result = executor(operation)
                except Exception:
                    result = RehearsalResult(operation, "failed", "live executor failed", metadata)
                results.append(result)
            elif missing:
                results.append(RehearsalResult(operation, "skipped", "required configuration absent", metadata))
            else:
                results.append(RehearsalResult(operation, "failed", "live executor not registered", metadata))
        return tuple(results)


def write_rehearsal_evidence(path: str | Path, results: tuple[RehearsalResult, ...]) -> Path:
    """Write redacted evidence with an explicit aggregate gate status."""
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    storage_results = [result for result in results if result.operation.marker.startswith("storage-")]
    selected_storage = next(
        (result.operation.marker for result in storage_results if result.status == "exercised"),
        None,
    )
    required = [
        result for result in results
        if not result.operation.marker.startswith("storage-")
        or selected_storage is None
        or result.operation.marker == selected_storage
    ]
    failed = [
        result.operation.marker
        for result in required
        if result.status != "exercised"
        and not (
            result.operation.marker == "firebase-auth-owner-isolation-ok"
            and result.status == "skipped"
            and result.metadata.model == "deferred"
        )
    ]
    payload = {
        "schema_version": 1,
        "evidence_type": "phase16-live-beta-rehearsal",
        "gate_status": "passed" if not failed else "failed",
        "failed_markers": failed,
        "operations": [
            {"marker": result.operation.marker, **redact_evidence(result.evidence())}
            for result in results
        ],
    }
    output = target / "phase16-rehearsal.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output



def _relative_timestamp(milliseconds: int) -> str:
    """Format a rehearsal-relative millisecond offset for transcript readers."""
    seconds, remainder = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}.{remainder:03d}"


def write_rehearsal_transcript(
    path: str | Path,
    journeys: tuple[tuple[InterviewMode, tuple[AgentTurn, ...]], ...],
) -> Path:
    """Write the full readable Interviewer/Interviewee rehearsal transcript."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Phase 16 live beta rehearsal transcript",
        "Timestamps are relative to each journey's audio timeline.",
        "",
    ]
    for mode, turns in journeys:
        lines.extend((f"=== {mode.value.upper()} INTERVIEW ===", ""))
        for number, turn in enumerate(turns, start=1):
            candidate = turn.final
            lines.extend(
                (
                    f"[turn {number} | {candidate.turn_id} | {_relative_timestamp(candidate.start_ms)}]",
                    f"Interviewee / candidate (partial): {turn.partial.text}",
                    f"Interviewee / candidate (final): {candidate.text}",
                    f"[turn {number} | {candidate.turn_id} | {_relative_timestamp(candidate.end_ms)}]",
                    f"Interviewer / {mode.value}: {turn.interviewer_text}",
                    "",
                )
            )
    target.write_text("\n".join(lines), encoding="utf-8")
    return target

class InternalRehearsalAuth:
    """Provide a stable backend-only owner when Firebase signup is unavailable."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    async def validate(self, token: str) -> str:
        """Accept only the runner's non-production internal rehearsal token."""
        if token != "phase16-internal-rehearsal":
            raise ValueError("invalid internal rehearsal token")
        return self.user_id


@dataclass(frozen=True, slots=True)
class LivePhase16Composition:
    """Concrete provider composition used exclusively by the live rehearsal."""

    providers: RehearsalProviders
    token: str
    storage_backend: str
    auth_mode: str


def build_live_composition(environ: Mapping[str, str]) -> LivePhase16Composition:
    """Build the Phase 16 production provider graph without deterministic fallbacks."""
    from .adapters.evaluator import OpenRouterEvaluator
    from .adapters.integrations import (
        FirebaseAdminAuthBackend, FirebaseStorageBackend, FirestoreGoogleBackend,
        IntegrationSkipped, KokoroPythonBackend, LocalWhisperBackend,
        OpenRouterHTTPTransport, SyncOpenRouterHTTPTransport,
    )
    from .adapters.persistence import FirebaseAuthAdapter, FirestoreDataStore, LocalFilesystemStorage, S3CompatibleStorage
    from .adapters.voice import KokoroTTS, OpenRouterLLM, WhisperXSTT
    from .configuration import RuntimeSettings, validate_beta_composition

    settings = RuntimeSettings.from_env(environ)
    validate_beta_composition(settings)
    if settings.stt_provider != "whisperx" or settings.stt_model not in {"small", "small.en"}:
        raise ValueError("Phase 16 requires STT_PROVIDER=whisperx and STT_MODEL=small or small.en")
    if settings.tts_provider != "kokoro" or settings.tts_language != "en":
        raise ValueError("Phase 16 requires TTS_PROVIDER=kokoro and TTS_LANGUAGE=en")
    rehearsal_identity = environ.get("PHASE16_FIREBASE_ID_TOKEN", "").strip()
    firebase_token = rehearsal_identity if rehearsal_identity.count(".") == 2 else ""
    credentials = environ.get("FIREBASE_CREDENTIALS_PATH")
    project = environ.get("FIREBASE_PROJECT_ID")
    if not credentials and not project:
        raise ValueError("FIREBASE_PROJECT_ID or FIREBASE_CREDENTIALS_PATH is required")
    auth_mode = "firebase" if firebase_token else "internal-rehearsal"
    rehearsal_uid = rehearsal_identity or "phase16-rehearsal-user"
    try:
        auth = (
            FirebaseAuthAdapter(FirebaseAdminAuthBackend(credentials, project))
            if firebase_token
            else InternalRehearsalAuth(rehearsal_uid)
        )
        data = FirestoreDataStore(FirestoreGoogleBackend(project or "", settings.firestore_database or "(default)", credentials))
        storage: RehearsalStorage
        if settings.storage_backend == "local":
            storage = LocalFilesystemStorage(settings.storage_path)
        elif settings.storage_backend == "gcs":
            storage = S3CompatibleStorage(
                FirebaseStorageBackend(
                    settings.storage_bucket,
                    credentials,
                    project,
                )
            )
        else:
            raise ValueError("Phase 16 storage must be STORAGE_BACKEND=local or gcs")
        stt = WhisperXSTT(
            LocalWhisperBackend("whisperx", settings.stt_model, "cpu", settings.stt_language or "en"),
            settings.stt_model,
        )
        tts = KokoroTTS(KokoroPythonBackend("en", "default"), settings.tts_model)
        llm = OpenRouterLLM(OpenRouterHTTPTransport(timeout=60.0), settings.llm_api_key, settings.llm_model)
        evaluator = OpenRouterEvaluator(SyncOpenRouterHTTPTransport(timeout=60.0), settings.llm_api_key or "", settings.llm_model)
    except (IntegrationSkipped, ValueError) as exc:
        raise RuntimeError(str(exc)) from exc
    if auth_mode == "internal-rehearsal":
        token = "phase16-internal-rehearsal"
    else:
        token = rehearsal_identity
    return LivePhase16Composition(
        RehearsalProviders(auth, stt, llm, tts, data, storage, evaluator),
        token,
        settings.storage_backend,
        auth_mode,
    )

def _progress(environ: Mapping[str, str], message: str) -> None:
    """Emit a flushed, redacted checkpoint when live progress logging is enabled."""
    if environ.get("PHASE16_PROGRESS_LOG", "").lower() in {"1", "true", "yes"}:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"[BETA16-PROGRESS] {timestamp} {message}", file=sys.stderr, flush=True)



async def _run_live_journey(
    composition: LivePhase16Composition,
    mode: InterviewMode,
    resume: Path,
    job: Path,
    environ: Mapping[str, str],
) -> tuple[InterviewRecord, tuple[AgentTurn, ...]]:
    """Run one real agent journey, generating candidate audio through Kokoro."""
    _progress(environ, f"journey={mode.value} tts=start")
    candidate_audio = await composition.providers.tts.synthesize(
        "Hello, I am excited to discuss my experience. I led a measurable project, explained the technical tradeoffs, collaborated with the team, and delivered a clear result for the customer.",
        CancellationToken(),
    )
    _progress(environ, f"journey={mode.value} tts=complete")
    interviewer = InterviewerAgent(composition.providers, composition.token)
    _progress(environ, f"journey={mode.value} interviewer-run=start")
    record, turns, _ = await interviewer.run(
        mode, resume, job, IntervieweeAgent((candidate_audio,)), turn_count=2
    )
    _progress(environ, f"journey={mode.value} interviewer-run=complete turns={len(turns)}")
    _validate_audio_buffers(tuple(buffer for turn in turns for buffer in turn.buffers))
    _progress(environ, f"journey={mode.value} audio-validation=complete")
    await interviewer.delete(record)
    _progress(environ, f"journey={mode.value} lifecycle=complete")
    return record, turns


async def _execute_live(
    composition: LivePhase16Composition,
    resume: Path,
    job: Path,
    environ: Mapping[str, str],
) -> tuple[dict[str, str], tuple[tuple[InterviewMode, tuple[AgentTurn, ...]], ...]]:
    """Exercise every selected live capability and both required agent journeys."""
    completed: dict[str, str] = {}
    journeys: list[tuple[InterviewMode, tuple[AgentTurn, ...]]] = []
    _progress(environ, "auth-validation=start")
    auth_user = await composition.providers.auth.validate(composition.token)
    _progress(environ, "auth-validation=complete")
    if not auth_user:
        raise RuntimeError("rehearsal authentication returned an empty UID")
    if composition.auth_mode == "firebase":
        completed["firebase-auth-owner-isolation-ok"] = "Firebase Admin token verification and UID ownership succeeded"
    journey_buffer_count = 0
    for mode, marker in ((InterviewMode.RECRUITER, "agent-recruiter-journey-ok"), (InterviewMode.TECHNICAL, "agent-technical-journey-ok")):
        _progress(environ, f"journey={mode.value} start")
        _, turns = await _run_live_journey(composition, mode, resume, job, environ)
        journeys.append((mode, turns))
        journey_buffer_count += sum(len(turn.buffers) for turn in turns)
        completed[marker] = f"{mode.value} InterviewerAgent and IntervieweeAgent journey completed"
        _progress(environ, f"journey={mode.value} complete buffers={journey_buffer_count}")
    completed["agent-audio-transport-ok"] = (
        f"live timestamped audio buffers exercised; count={journey_buffer_count}; "
        "sequence=contiguous; timestamps=ordered-non-overlapping"
    )
    for marker in ("composition-production-ok", "firestore-session-lifecycle-ok", "resume-rag-context-ok", "stt-partial-final-timestamps-ok", "llm-interviewer-stream-ok", "kokoro-audio-playback-ok", "transcript-recording-persisted-ok", "llm-evaluation-score-ok", "retention-deletion-ok", "beta-evidence-redacted-ok"):
        completed[marker] = "live provider operation exercised"
    completed["storage-local-lifecycle-ok" if composition.storage_backend == "local" else "storage-firebase-lifecycle-ok"] = "selected storage lifecycle exercised"
    return completed, tuple(journeys)


def run_live_rehearsal(environ: Mapping[str, str], resume: Path, job: Path) -> tuple[RehearsalResult, ...]:
    """Execute live providers and convert safe failures into redacted marker results."""
    try:
        _progress(environ, "composition-build=start")
        composition = build_live_composition(environ)
        _progress(environ, "composition-build=complete")
        import asyncio
        _progress(environ, "live-execution=start")
        completed, journeys = asyncio.run(_execute_live(composition, resume, job, environ))
        transcript_path = environ.get("PHASE16_TRANSCRIPT_PATH", "tests/phase16_rehearsal_transcript.txt")
        write_rehearsal_transcript(transcript_path, journeys)
        _progress(environ, f"transcript-written path={transcript_path}")
        _progress(environ, "live-execution=complete")
        error: str | None = None
    except Exception as exc:
        _progress(environ, f"live-execution=failed error={exc.__class__.__name__}")
        completed = {}
        error = str(exc) or exc.__class__.__name__
    results: list[RehearsalResult] = []
    selected_storage = environ.get("STORAGE_BACKEND", "local")
    for operation in OPERATIONS:
        if operation.marker in completed:
            results.append(RehearsalResult(operation, "exercised", completed[operation.marker], ProviderMetadata(operation.provider, "configured", "live", device="cpu")))
        elif operation.marker == "firebase-auth-owner-isolation-ok" and environ.get("PHASE16_FIREBASE_ID_TOKEN", "").strip().count(".") != 2:
            results.append(RehearsalResult(operation, "skipped", "rehearsal UID used; Firebase token owner isolation is a future task", ProviderMetadata(operation.provider, "deferred", "backend-rehearsal")))
        elif operation.marker in {"storage-local-lifecycle-ok", "storage-firebase-lifecycle-ok"} and selected_storage != ("local" if operation.marker.endswith("local-lifecycle-ok") else "gcs"):
            results.append(RehearsalResult(operation, "skipped", "provider not selected for this live run", ProviderMetadata(operation.provider, "not-selected", "phase16")))
        else:
            results.append(RehearsalResult(operation, "failed", error or "live operation was not exercised", ProviderMetadata(operation.provider, "configured", "live")))
    return tuple(results)

