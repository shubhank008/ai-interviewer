"""Concrete provider adapters grouped by capability."""

from .evaluator import OpenRouterEvaluator
from .voice import FasterWhisperSTT, OpenRouterLLM, PiperKokoroTTS

__all__ = ["FasterWhisperSTT", "OpenRouterEvaluator", "OpenRouterLLM", "PiperKokoroTTS"]
