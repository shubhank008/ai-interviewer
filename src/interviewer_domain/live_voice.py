"""Provider-independent orchestration for a cancellable live voice turn."""

from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from typing import AsyncIterator, Sequence
from uuid import UUID, uuid4

from .contracts import (
    CancellationToken,
    DataStore,
    ErrorCode,
    EventBus,
    ProviderError,
    SecondaryResponseProvider,
    StreamAudioChunk,
    StreamTextChunk,
    StreamingLLMProvider,
    StreamingSTTProvider,
    StreamingTTSProvider,
)
from .models import InterviewSession, LifecycleEvent, Recording, TranscriptSegment, Turn


@dataclass(frozen=True, slots=True)
class TimestampedAudio:
    """An audio artifact retained separately from control-channel events."""

    session_id: UUID
    turn_id: UUID
    sequence: int
    audio: bytes
    start_ms: int
    end_ms: int
    speaker: str = "interviewer"


@dataclass(frozen=True, slots=True)
class PrefetchedResponse:
    """A response candidate valid only for one exact answer digest."""

    source_turn_sequence: int
    answer_digest: str
    text: str


@dataclass(frozen=True, slots=True)
class LiveVoiceTurnResult:
    """Summary of one live turn, including interruption and latency evidence."""

    response: str
    transcript: tuple[TranscriptSegment, ...]
    audio: tuple[TimestampedAudio, ...]
    latency_ms: int
    interrupted: bool = False
    fallback_count: int = 0


class AudioScheduler:
    """Schedule ordered audio chunks and stop future playback on interruption."""

    def __init__(self) -> None:
        self._interrupted = False
        self.played: list[TimestampedAudio] = []

    def interrupt(self) -> None:
        """Prevent any not-yet-scheduled chunk from being played."""
        self._interrupted = True

    async def schedule(self, session_id: UUID, turn_id: UUID, chunks: AsyncIterator[StreamAudioChunk]) -> tuple[TimestampedAudio, ...]:
        """Consume chunks in sequence order until interruption or exhaustion."""
        pending: list[StreamAudioChunk] = []
        async for chunk in chunks:
            if self._interrupted:
                break
            pending.append(chunk)
        pending.sort(key=lambda item: item.sequence)
        output = tuple(
            TimestampedAudio(session_id, turn_id, item.sequence, item.audio, item.start_ms, item.start_ms + item.duration_ms)
            for item in pending
            if not self._interrupted
        )
        self.played.extend(output)
        return output


class PrefetchGuard:
    """Keep speculative work bounded and reject work from changed answers."""

    def __init__(self, maximum: int = 2) -> None:
        self.maximum = maximum
        self._items: list[PrefetchedResponse] = []

    def add(self, item: PrefetchedResponse) -> None:
        """Retain only the newest bounded speculative responses."""
        self._items.append(item)
        self._items = self._items[-self.maximum :]

    def take(self, answer: str, sequence: int) -> PrefetchedResponse | None:
        """Return a response only when its source sequence and digest match."""
        digest = _digest(answer)
        for item in reversed(self._items):
            if item.source_turn_sequence == sequence and item.answer_digest == digest:
                self._items.remove(item)
                return item
        self._items.clear()
        return None


def _digest(value: str) -> str:
    """Return a stable digest for speculative-context comparison."""
    return sha256(value.encode("utf-8")).hexdigest()


class LiveVoiceOrchestrator:
    """Connect streaming capabilities to the existing interview domain seams."""

    def __init__(
        self,
        session: InterviewSession,
        stt: Sequence[StreamingSTTProvider],
        llm: Sequence[StreamingLLMProvider],
        tts: Sequence[StreamingTTSProvider],
        store: DataStore,
        events: EventBus,
        secondary: SecondaryResponseProvider | None = None,
    ) -> None:
        if not stt or not llm or not tts:
            raise ValueError("live voice requires at least one STT, LLM, and TTS provider")
        self.session = session
        self.stt = tuple(stt)
        self.llm = tuple(llm)
        self.tts = tuple(tts)
        self.store = store
        self.events = events
        self.secondary = secondary
        self.scheduler = AudioScheduler()
        self.prefetch = PrefetchGuard()
        self._event_sequence = 0
        self._correlation_id = str(uuid4())
        self._active_token: CancellationToken | None = None
        self._fallback_count = 0
        self.artifacts: list[TimestampedAudio] = []

    async def prefetch_response(self, answer: str, sequence: int) -> PrefetchedResponse:
        """Prepare bounded speculative secondary work keyed to the current answer."""
        if self.secondary is None:
            text = ""
        else:
            text = await self.secondary.generate_secondary(answer, CancellationToken())
        item = PrefetchedResponse(sequence, _digest(answer), self._bound_secondary(text))
        self.prefetch.add(item)
        return item

    def accept_prefetch(self, answer: str, sequence: int) -> str | None:
        """Accept matching speculation or discard it as stale."""
        item = self.prefetch.take(answer, sequence)
        return item.text if item else None

    def interrupt(self) -> None:
        """Cancel provider work and stop all future audio playback."""
        if self._active_token is not None:
            self._active_token.cancel()
        self.scheduler.interrupt()

    async def process_turn(self, turn: Turn, token: CancellationToken | None = None) -> LiveVoiceTurnResult:
        """Run incremental STT, cancellable response generation, and TTS scheduling."""
        started = monotonic()
        operation_token = token or CancellationToken()
        self._active_token = operation_token
        self.store.link_turn_session(turn.id, turn.session_id)
        await self._emit("live.turn.started", {"turn_id": str(turn.id)})
        transcript: list[TranscriptSegment] = []
        try:
            async for segment in self._stream_stt(turn.input_audio, turn.id, operation_token):
                transcript.append(segment)
                self.store.save_transcript(segment)
            if not transcript or not transcript[-1].text.strip():
                raise ProviderError(ErrorCode.INVALID_REQUEST, "streaming STT returned no text")
            answer = transcript[-1].text
            await self._emit("transcript.final", {"turn_id": str(turn.id), "text": answer})
            secondary_text = self.accept_prefetch(answer, turn.sequence) if self.prefetch else None
            if secondary_text is None and self.secondary is not None:
                secondary_text = self._bound_secondary(await self.secondary.generate_secondary(answer, operation_token))
            if secondary_text:
                await self._emit("secondary.response", {"turn_id": str(turn.id), "text": secondary_text})
            response_parts: list[str] = []
            async for chunk in self._stream_llm(answer, operation_token):
                response_parts.append(chunk.text)
                await self._emit("response.chunk", {"turn_id": str(turn.id), "sequence": str(chunk.sequence), "text": chunk.text})
            response = "".join(response_parts)
            audio = await self.scheduler.schedule(turn.session_id, turn.id, self._stream_tts(response, operation_token))
            self.artifacts.extend(audio)
            self.store.save_recording(Recording(turn.session_id, f"live/{turn.id}", "audio/mock", audio[-1].end_ms if audio else 0))
            latency = int((monotonic() - started) * 1000)
            await self._emit("live.latency", {"turn_id": str(turn.id), "latency_ms": str(latency)})
            await self._emit("live.turn.completed", {"turn_id": str(turn.id)})
            return LiveVoiceTurnResult(response, tuple(transcript), audio, latency, False, self._fallback_count)
        except ProviderError as error:
            if error.code == ErrorCode.CANCELLED:
                latency = int((monotonic() - started) * 1000)
                await self._emit("playback.interrupted", {"turn_id": str(turn.id)})
                return LiveVoiceTurnResult("", tuple(transcript), tuple(self.scheduler.played), latency, True, self._fallback_count)
            await self._emit("live.turn.failed", {"turn_id": str(turn.id), "code": error.code.value})
            raise
        finally:
            self._active_token = None

    async def _stream_stt(self, audio: bytes, turn_id: UUID, token: CancellationToken) -> AsyncIterator[TranscriptSegment]:
        """Try incremental STT providers in configured order."""
        for index, provider in enumerate(self.stt):
            try:
                if index:
                    await self._fallback("stt", index)
                async for segment in provider.transcribe_stream(audio, turn_id, token):
                    await self._emit("transcript.partial" if not segment.is_final else "transcript.final", {"turn_id": str(turn_id), "text": segment.text})
                    yield segment
                return
            except ProviderError as error:
                if error.code == ErrorCode.CANCELLED or index == len(self.stt) - 1:
                    raise

    async def _stream_llm(self, prompt: str, token: CancellationToken) -> AsyncIterator[StreamTextChunk]:
        """Try cancellable response streams in configured order."""
        for index, provider in enumerate(self.llm):
            try:
                if index:
                    await self._fallback("llm", index)
                async for chunk in provider.generate_stream(prompt, token):
                    yield chunk
                return
            except ProviderError as error:
                if error.code == ErrorCode.CANCELLED or index == len(self.llm) - 1:
                    raise

    async def _stream_tts(self, text: str, token: CancellationToken) -> AsyncIterator[StreamAudioChunk]:
        """Try cancellable audio streams in configured order."""
        for index, provider in enumerate(self.tts):
            try:
                if index:
                    await self._fallback("tts", index)
                async for chunk in provider.synthesize_stream(text, token):
                    yield chunk
                return
            except ProviderError as error:
                if error.code == ErrorCode.CANCELLED or index == len(self.tts) - 1:
                    raise

    async def _fallback(self, capability: str, provider_index: int) -> None:
        """Emit a safe provider fallback event without naming a vendor."""
        self._fallback_count += 1
        await self._emit("provider.fallback", {"capability": capability, "provider_index": str(provider_index)})

    async def _emit(self, name: str, payload: dict[str, str]) -> None:
        """Publish an ordered event through the Phase 5-compatible event seam."""
        self._event_sequence += 1
        await self.events.publish(LifecycleEvent(self.session.id, name, self._event_sequence, payload, correlation_id=self._correlation_id))

    @staticmethod
    def _bound_secondary(text: str) -> str:
        """Apply the deliberately small secondary-response safety boundary."""
        return text.strip()[:160]
