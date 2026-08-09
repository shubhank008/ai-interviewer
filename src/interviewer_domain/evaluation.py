"""Provider-independent, deterministic post-interview evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol
from uuid import UUID

from .contracts import ErrorCode, ProviderError
from .models import Evaluation, InterviewMode, TranscriptSegment
from .persistence import InterviewRecord

EVALUATION_VERSION = "phase8-v1"
MAX_EVIDENCE_REFERENCES = 3


@dataclass(frozen=True, slots=True)
class InterviewContext:
    """Context retained from setup and supplied to a post-interview evaluator."""

    mode: InterviewMode
    role: str
    seniority: str
    job_description: str = ""
    resume: str = ""


@dataclass(frozen=True, slots=True)
class RubricDimension:
    """One versioned scoring dimension and its normalized weight."""

    key: str
    label: str
    weight: float
    positive_terms: tuple[str, ...]
    negative_terms: tuple[str, ...] = ()


class Evaluator(Protocol):
    """Replaceable evaluator capability for future model-backed providers."""

    def evaluate(
        self, context: InterviewContext, transcript: tuple[TranscriptSegment, ...]
    ) -> Evaluation: ...


class EvaluationDataStore(Protocol):
    """Owned persistence capability required by the post-interview service."""

    def get_interview(self, user_id: str, interview_id: UUID) -> InterviewRecord: ...

    def save_evaluation(
        self, user_id: str, interview_id: UUID, evaluation: Evaluation
    ) -> None: ...


def _rubric(mode: InterviewMode) -> tuple[RubricDimension, ...]:
    """Return the initial mode-specific rubric with intentionally fresh weights."""
    if mode is InterviewMode.RECRUITER:
        return (
            RubricDimension(
                "communication",
                "Communication and clarity",
                0.25,
                ("clear", "communicat", "explain"),
                ("unclear", "confus"),
            ),
            RubricDimension(
                "motivation",
                "Role relevance and motivation",
                0.20,
                ("motivat", "interested", "role", "company"),
                ("unsure", "any role"),
            ),
            RubricDimension(
                "impact",
                "Evidence of impact and ownership",
                0.20,
                ("led", "owned", "impact", "improv", "delivered"),
                ("assisted", "helped"),
            ),
            RubricDimension(
                "collaboration",
                "Behavioral signals and collaboration",
                0.20,
                ("team", "collaborat", "feedback", "conflict"),
                ("alone", "blame"),
            ),
            RubricDimension(
                "readiness",
                "Interview readiness and response quality",
                0.15,
                ("example", "result", "question", "available"),
                ("not sure", "no example"),
            ),
        )
    return (
        RubricDimension(
            "technical_depth",
            "Technical depth or domain understanding",
            0.25,
            ("architect", "design", "system", "technical", "tradeoff"),
            ("guess", "not familiar"),
        ),
        RubricDimension(
            "problem_solving",
            "Problem solving and reasoning",
            0.25,
            ("problem", "reason", "debug", "approach", "tradeoff"),
            ("random", "stuck"),
        ),
        RubricDimension(
            "impact",
            "Evidence of impact and ownership",
            0.20,
            ("led", "owned", "impact", "scale", "delivered"),
            ("assisted", "helped"),
        ),
        RubricDimension(
            "communication",
            "Communication and clarity",
            0.15,
            ("clear", "explain", "because", "first", "then"),
            ("unclear", "confus"),
        ),
        RubricDimension(
            "behavioral",
            "Behavioral signals and collaboration",
            0.15,
            ("team", "collaborat", "feedback", "stakeholder"),
            ("blame", "alone"),
        ),
    )


def normalized_rubric(mode: InterviewMode) -> tuple[RubricDimension, ...]:
    """Return a rubric whose weights sum to exactly one after rounding."""
    dimensions = _rubric(mode)
    total = sum(dimension.weight for dimension in dimensions)
    weights = [round(dimension.weight / total, 6) for dimension in dimensions]
    weights[-1] = round(1.0 - sum(weights[:-1]), 6)
    return tuple(
        RubricDimension(
            d.key, d.label, weights[index], d.positive_terms, d.negative_terms
        )
        for index, d in enumerate(dimensions)
    )


def _clip(value: float) -> int:
    """Round a score and enforce the public 0-100 bound."""
    return max(0, min(100, round(value)))


class DeterministicEvaluator:
    """Score final candidate transcript text using transparent lexical evidence."""

    def __init__(self, rubric_version: str = EVALUATION_VERSION) -> None:
        self.rubric_version = rubric_version

    def evaluate(
        self, context: InterviewContext, transcript: tuple[TranscriptSegment, ...]
    ) -> Evaluation:
        """Build a reproducible evaluation without network, credentials, or an LLM."""
        if not transcript:
            raise ProviderError(
                ErrorCode.INVALID_REQUEST, "cannot evaluate an empty transcript"
            )
        candidate = tuple(
            segment
            for segment in transcript
            if segment.speaker == "candidate"
            and segment.is_final
            and segment.text.strip()
        )
        if not candidate:
            raise ProviderError(
                ErrorCode.INVALID_REQUEST, "transcript has no final candidate evidence"
            )
        dimensions: list[dict[str, object]] = []
        weighted_total = 0.0
        for dimension in normalized_rubric(context.mode):
            matches = [
                segment
                for segment in candidate
                if any(
                    term in segment.text.lower() for term in dimension.positive_terms
                )
            ]
            negatives = [
                segment
                for segment in candidate
                if any(
                    term in segment.text.lower() for term in dimension.negative_terms
                )
            ]
            ambiguous = bool(matches and negatives)
            confidence = (
                0.0
                if not matches
                else (0.5 if ambiguous else min(1.0, 0.7 + 0.1 * len(matches)))
            )
            score = 45 if not matches else 72 + min(23, len(matches) * 7)
            if ambiguous:
                score -= 10
            score = _clip(score)
            weighted_total += dimension.weight * score
            dimensions.append(
                {
                    "key": dimension.key,
                    "label": dimension.label,
                    "weight": dimension.weight,
                    "score": score,
                    "confidence": round(confidence, 2),
                    "evidence_status": "ambiguous"
                    if ambiguous
                    else ("supported" if matches else "missing"),
                    "evidence": tuple(
                        {
                            "turn_id": str(segment.turn_id),
                            "speaker": segment.speaker,
                            "quote": segment.text[:240],
                        }
                        for segment in matches[:MAX_EVIDENCE_REFERENCES]
                    ),
                    "explanation": "Evidence supports this dimension."
                    if matches
                    else "No direct final candidate evidence was found; this is a gap, not an inferred claim.",
                }
            )
        overall = _clip(weighted_total)
        supported = [
            item["label"]
            for item in dimensions
            if item["evidence_status"] == "supported"
        ]
        missing = [
            item["label"]
            for item in dimensions
            if item["evidence_status"] != "supported"
        ]
        mode_label = (
            "recruiter" if context.mode is InterviewMode.RECRUITER else "technical"
        )
        return Evaluation(
            session_id=transcript[0].turn_id,
            rubric_version=self.rubric_version,
            score=overall,
            dimensions=tuple(dimensions),
            mode=context.mode.value,
            context={
                "role": context.role,
                "seniority": context.seniority,
                "job_description": context.job_description,
                "resume": context.resume,
            },
            summary=f"A {mode_label} interview evaluation based only on the final candidate transcript.",
            strengths=tuple(
                f"Demonstrated evidence in {label}." for label in supported
            ),
            weaknesses=tuple(
                f"Limited or mixed evidence for {label}." for label in missing
            ),
            recommendations=tuple(
                f"Prepare a specific STAR-style example for {label}."
                for label in missing
            ),
        )


class PostInterviewEvaluationService:
    """Authorize, evaluate, and persist a completed interview through interfaces."""

    def __init__(
        self, data: EvaluationDataStore, evaluator: Evaluator | None = None
    ) -> None:
        self.data = data
        self.evaluator = evaluator or DeterministicEvaluator()

    def evaluate(
        self,
        user_id: str,
        interview_id: UUID,
        context: InterviewContext,
        transcript: tuple[TranscriptSegment, ...],
    ) -> Evaluation:
        """Evaluate only an owned completed interview and persist its result."""
        record = self.data.get_interview(user_id, interview_id)
        if record.status != "completed":
            raise ProviderError(
                ErrorCode.CONFLICT, "evaluation requires a completed interview"
            )
        if context.mode is not record.mode:
            raise ProviderError(
                ErrorCode.CONFLICT, "evaluation context mode does not match interview"
            )
        result = self.evaluator.evaluate(context, transcript)
        result = Evaluation(
            interview_id,
            result.rubric_version,
            result.score,
            result.dimensions,
            result.mode,
            result.context,
            result.summary,
            result.strengths,
            result.weaknesses,
            result.recommendations,
        )
        self.data.save_evaluation(user_id, interview_id, result)
        return result


def evaluation_dict(evaluation: Evaluation) -> dict[str, object]:
    """Return a JSON-safe structured result for a results resource."""
    value = asdict(evaluation)
    value["session_id"] = str(evaluation.session_id)
    return value
