"""Compatibility exports for provider adapters.

New code must import concrete adapters from ``interviewer_domain.adapters``.
"""

from .adapters.voice import (
    FasterWhisperSTT,
    KokoroOnnxTTS,
    KokoroTTS,
    OpenAIWhisperSTT,
    OpenRouterLLM,
    OpenRouterTransport,
    PiperKokoroTTS,
    SpeechBackend,
    WhisperBackend,
    WhisperXSTT,
)

__all__ = [
    "FasterWhisperSTT",
    "KokoroOnnxTTS",
    "KokoroTTS",
    "OpenAIWhisperSTT",
    "OpenRouterLLM",
    "OpenRouterTransport",
    "PiperKokoroTTS",
    "SpeechBackend",
    "WhisperBackend",
    "WhisperXSTT",
]
