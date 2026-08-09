"""Provider-independent interview session state machine."""

from dataclasses import replace
from hashlib import sha256
from uuid import UUID, uuid4

from .contracts import CancellationToken, DataStore, EventBus, LLMProvider, ProviderError, STTProvider, TTSProvider
from .models import InterviewSession, LifecycleEvent, QuestionPlan, SessionStatus, Turn


class SessionStateError(ValueError):
    """Raised when an operation violates session state or turn ordering."""


class QuestionPlanner:
    """Prepare mode-specific questions without binding the session to a script."""

    _TOPICS = {
        "recruiter": ("motivation", "Tell me about your background and why this role interests you."),
        "technical": ("technical-depth", "Describe a technically challenging project you owned and the trade-offs you made."),
    }

    def initial(self, session: InterviewSession) -> QuestionPlan:
        """Create the first question for a session's selected mode."""
        topic, prompt = self._TOPICS[session.mode.value]
        return self._make(session, topic, prompt, 0)

    def follow_up(self, session: InterviewSession, answer: str, sequence: int) -> QuestionPlan:
        """Prepare one follow-up grounded in the latest answer."""
        if not answer.strip():
            raise SessionStateError("cannot plan from an empty answer")
        if session.mode.value == "recruiter":
            topic = "role-fit" if "role" in answer.lower() else "impact"
            prompt = "What specifically attracted you to this role, and what impact would you hope to make?"
        else:
            topic = "problem-solving" if any(word in answer.lower() for word in ("trade-off", "problem", "design")) else "technical-depth"
            prompt = "What was the hardest technical decision, and how did you validate the result?"
        return self._make(session, topic, prompt, sequence, answer)

    def is_current(self, plan: QuestionPlan, answer: str, sequence: int) -> bool:
        """Accept a plan only when its source context still matches the answer."""
        return plan.source_turn_sequence == sequence and plan.context_digest == self._digest(answer)

    def _make(self, session: InterviewSession, topic: str, prompt: str, sequence: int, context: str = "") -> QuestionPlan:
        return QuestionPlan(session.id, session.mode, topic, prompt, sequence, self._digest(context))

    @staticmethod
    def _digest(value: str) -> str:
        return sha256(value.encode("utf-8")).hexdigest()


class InterviewSessionEngine:
    """Run ordered interview turns through Phase 1 capability interfaces."""

    def __init__(self, session: InterviewSession, stt: STTProvider, llm: LLMProvider, tts: TTSProvider, store: DataStore, events: EventBus, planner: QuestionPlanner | None = None) -> None:
        self.session = replace(session, status=SessionStatus.CREATED.value)
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.store = store
        self.events = events
        self.planner = planner or QuestionPlanner()
        self._next_event_sequence = 0
        self._expected_turn = 1
        self._last_answer = ""
        self._plan: QuestionPlan | None = None
        self._correlation_id = str(uuid4())

    @property
    def question_plan(self) -> QuestionPlan | None:
        """Return the current advisory question plan."""
        return self._plan

    async def start(self) -> QuestionPlan:
        """Activate a newly created session and emit its opening events."""
        self._require_status(SessionStatus.CREATED)
        self.session = replace(self.session, status=SessionStatus.ACTIVE.value)
        await self._emit("session.started")
        await self._emit("session.active")
        self._plan = self.planner.initial(self.session)
        await self._emit("question.prepared", {"topic": self._plan.topic})
        return self._plan

    async def process_turn(self, turn: Turn, token: CancellationToken | None = None) -> tuple[str, bytes]:
        """Process exactly the next candidate turn and prepare its follow-up."""
        self._require_status(SessionStatus.ACTIVE)
        if turn.session_id != self.session.id or turn.sequence != self._expected_turn or turn.speaker != "candidate":
            raise SessionStateError("turn does not match the expected session sequence")
        operation_token = token or CancellationToken()
        self.store.link_turn_session(turn.id, turn.session_id)
        await self._emit("turn.started", correlation=turn.id)
        try:
            await self._emit("turn.processing", correlation=turn.id)
            transcript = await self.stt.transcribe(turn.input_audio, turn.id, operation_token)
            self.store.save_transcript(transcript)
            self._last_answer = transcript.text
            response = await self.llm.generate(transcript.text, operation_token)
            audio = await self.tts.synthesize(response, operation_token)
            self._plan = self.planner.follow_up(self.session, transcript.text, turn.sequence)
            self._expected_turn += 1
            await self._emit("turn.completed", correlation=turn.id)
            await self._emit("question.prepared", {"topic": self._plan.topic}, turn.id)
            return response, audio
        except ProviderError as error:
            terminal = SessionStatus.CANCELLED if error.code.value == "cancelled" else SessionStatus.FAILED
            self.session = replace(self.session, status=terminal.value)
            await self._emit("session.cancelled" if terminal is SessionStatus.CANCELLED else "session.failed", correlation=turn.id)
            raise
        except Exception:
            self.session = replace(self.session, status=SessionStatus.FAILED.value)
            await self._emit("session.failed", correlation=turn.id)
            raise

    async def cancel(self) -> None:
        """Cancel an active session without emitting completion."""
        self._require_status(SessionStatus.ACTIVE)
        self.session = replace(self.session, status=SessionStatus.CANCELLED.value)
        await self._emit("session.cancelled")

    async def complete(self) -> None:
        """Complete an active session after its current work is finished."""
        self._require_status(SessionStatus.ACTIVE)
        self.session = replace(self.session, status=SessionStatus.COMPLETED.value)
        await self._emit("session.completed")

    def is_plan_current(self, answer: str) -> bool:
        """Report whether the prepared plan still matches the latest turn context."""
        return self._plan is not None and self.planner.is_current(self._plan, answer, self._expected_turn - 1)

    def _require_status(self, expected: SessionStatus) -> None:
        if self.session.status != expected.value:
            raise SessionStateError(f"session must be {expected.value}, got {self.session.status}")

    async def _emit(self, name: str, payload: dict[str, str] | None = None, correlation: UUID | None = None) -> None:
        self._next_event_sequence += 1
        event_payload = dict(payload or {})
        if correlation is not None:
            event_payload["turn_id"] = str(correlation)
        await self.events.publish(LifecycleEvent(self.session.id, name, self._next_event_sequence, event_payload, correlation_id=self._correlation_id))
