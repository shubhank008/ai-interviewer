"""Concrete provider adapters grouped by capability."""

from .ending import AdaptiveEndingProvider
from .evaluator import OpenRouterEvaluator
from .voice import FasterWhisperSTT, OpenRouterLLM, PiperKokoroTTS

__all__ = ["AdaptiveEndingProvider", "FasterWhisperSTT", "OpenRouterEvaluator", "OpenRouterLLM", "PiperKokoroTTS"]
