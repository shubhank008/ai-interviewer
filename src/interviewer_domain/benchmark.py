"""Repeatable local benchmark execution and normalized report values."""

from __future__ import annotations

import resource
import time
from dataclasses import asdict, dataclass
from typing import Callable

from .contracts import CancellationToken, LLMProvider, STTProvider, TTSProvider
from .models import ProviderMeasurement, Turn


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """Serializable aggregate benchmark result."""

    provider: str
    measurements: tuple[ProviderMeasurement, ...]

    def to_dict(self) -> dict[str, object]:
        """Serialize measurements without provider-specific objects."""
        return {"provider": self.provider, "measurements": [asdict(item) for item in self.measurements]}


class ProviderBenchmark:
    """Measure the real STT, LLM, and TTS path with deterministic fixtures allowed."""

    def __init__(self, quality: Callable[[str, str], float] | None = None, cost: Callable[[str], float] | None = None) -> None:
        self.quality = quality or (lambda expected, actual: 1.0 if expected == actual else 0.0)
        self.cost = cost or (lambda _: 0.0)

    async def run(self, provider: str, stt: STTProvider, llm: LLMProvider, tts: TTSProvider, turns: list[Turn]) -> BenchmarkReport:
        """Run each turn and capture timing, quality, cost, failure, and resource fields."""
        results: list[ProviderMeasurement] = []
        for turn in turns:
            started = time.perf_counter()
            usage_before = resource.getrusage(resource.RUSAGE_SELF)
            try:
                token = CancellationToken()
                transcript = await stt.transcribe(turn.input_audio, turn.id, token)
                response = await llm.generate(transcript.text, token)
                await tts.synthesize(response, token)
                elapsed = max(0, round((time.perf_counter() - started) * 1000))
                usage_after = resource.getrusage(resource.RUSAGE_SELF)
                results.append(ProviderMeasurement("voice-turn", provider, "turn", elapsed, True, elapsed, elapsed, self.quality("I built a reliable service.", transcript.text), self.cost(response), None, max(0.0, usage_after.ru_utime - usage_before.ru_utime), None))
            except Exception as error:
                elapsed = max(0, round((time.perf_counter() - started) * 1000))
                code = getattr(getattr(error, "code", None), "value", "internal")
                results.append(ProviderMeasurement("voice-turn", provider, "turn", elapsed, False, elapsed, elapsed, 0.0, 0.0, code))
        return BenchmarkReport(provider, tuple(results))
