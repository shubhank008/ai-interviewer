"""Compatibility exports for provider adapters.

New code must import concrete adapters from ``interviewer_domain.adapters``.
"""

from .adapters.voice import (
    FasterWhisperSTT,
    OpenRouterLLM,
    OpenRouterTransport,
    PiperKokoroTTS,
    SpeechBackend,
    WhisperBackend,
)

__all__ = [
    "FasterWhisperSTT",
    "OpenRouterLLM",
    "OpenRouterTransport",
    "PiperKokoroTTS",
    "SpeechBackend",
    "WhisperBackend",
]
