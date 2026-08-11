"""Concrete post-interview evaluator backed by OpenRouter."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from ..contracts import ErrorCode, ProviderError
from ..evaluation import EVALUATION_VERSION, Evaluator, InterviewContext
from ..models import Evaluation, TranscriptSegment
from .voice import OpenRouterTransport


class OpenRouterEvaluator(Evaluator):
    """Evaluate a completed transcript through a structured OpenRouter response."""

    def __init__(self, transport: OpenRouterTransport, api_key: str, model: str, rubric_version: str = EVALUATION_VERSION) -> None:
        self.transport = transport
        self.api_key = api_key
        self.model = model
        self.rubric_version = rubric_version

    def evaluate(self, context: InterviewContext, transcript: tuple[TranscriptSegment, ...]) -> Evaluation:
        """Request and validate bounded feedback from the final transcript only."""
        if not self.api_key or not self.model:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "evaluator configuration is missing")
        if not transcript:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "cannot evaluate an empty transcript")
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Evaluate a completed mock interview. Return JSON only with keys score, dimensions, summary, strengths, weaknesses, recommendations. Score must be an integer from 0 to 100. Do not invent facts."},
                {"role": "user", "content": json.dumps({
                    "mode": context.mode.value,
                    "role": context.role,
                    "seniority": context.seniority,
                    "job_description": context.job_description,
                    "transcript": [{"speaker": item.speaker, "text": item.text, "final": item.is_final} for item in transcript],
                }, ensure_ascii=False)},
            ],
        }
        try:
            response = asyncio.run(self.transport.complete(payload, self.api_key))
            content = response["choices"][0]["message"]["content"]
            value = json.loads(content) if isinstance(content, str) else content
            return self._normalize(value, context, transcript)
        except ProviderError:
            raise
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError(ErrorCode.INTERNAL, "evaluator response was malformed") from exc
        except RuntimeError as exc:
            raise ProviderError(ErrorCode.INTERNAL, "evaluator cannot run inside an active event loop") from exc

    def _normalize(self, value: Any, context: InterviewContext, transcript: tuple[TranscriptSegment, ...]) -> Evaluation:
        """Validate model output and discard fields outside the public schema."""
        if not isinstance(value, dict):
            raise ProviderError(ErrorCode.INTERNAL, "evaluator response was not an object")
        score = value.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise ProviderError(ErrorCode.INTERNAL, "evaluator score was outside 0 to 100")
        dimensions = value.get("dimensions", [])
        if not isinstance(dimensions, list) or not all(isinstance(item, dict) for item in dimensions):
            raise ProviderError(ErrorCode.INTERNAL, "evaluator dimensions were malformed")
        def strings(key: str) -> tuple[str, ...]:
            values = value.get(key, [])
            return tuple(str(item)[:500] for item in values if item) if isinstance(values, list) else ()
        return Evaluation(
            session_id=transcript[0].turn_id,
            rubric_version=self.rubric_version,
            score=round(score),
            dimensions=tuple(dimensions[:10]),
            mode=context.mode.value,
            context={"role": context.role, "seniority": context.seniority},
            summary=str(value.get("summary", ""))[:2000],
            strengths=strings("strengths"),
            weaknesses=strings("weaknesses"),
            recommendations=strings("recommendations"),
        )
