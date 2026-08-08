"""Provider-independent composition for a deterministic voice-shaped turn."""

from .contracts import CancellationToken, DataStore, EventBus, LLMProvider, STTProvider, TTSProvider
from .models import LifecycleEvent, Recording, Turn


class MockTurnRunner:
    """Run STT, LLM, and TTS in order while persisting lifecycle evidence."""

    def __init__(self, stt: STTProvider, llm: LLMProvider, tts: TTSProvider, store: DataStore, events: EventBus) -> None:
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.store = store
        self.events = events

    async def run(self, turn: Turn, token: CancellationToken | None = None) -> tuple[str, bytes]:
        """Process one candidate audio turn and return response text and audio."""
        operation_token = token or CancellationToken()
        await self.events.publish(LifecycleEvent(turn.session_id, "turn.started", 1, {"turn_id": str(turn.id)}))
        try:
            await self.events.publish(LifecycleEvent(turn.session_id, "turn.processing", 2))
            transcript = await self.stt.transcribe(turn.input_audio, turn.id, operation_token)
            self.store.save_transcript(transcript)
            response = await self.llm.generate(transcript.text, operation_token)
            audio = await self.tts.synthesize(response, operation_token)
            self.store.save_recording(Recording(turn.session_id, f"turn/{turn.id}", "audio/mock"))
            await self.events.publish(LifecycleEvent(turn.session_id, "turn.completed", 3))
            return response, audio
        except Exception:
            await self.events.publish(LifecycleEvent(turn.session_id, "turn.failed", 3))
            raise
