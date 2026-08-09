"""Domain and capability foundation for the voice-first interview platform."""

from .models import (
    DocumentChunk,
    DocumentSource,
    InterviewMode,
    InterviewSession,
    QuestionPlan,
    RetrievedEvidence,
    SessionStatus,
    Turn,
)
from .documents import LocalDocumentParser
from .retrieval import DeterministicEmbeddingProvider, InMemoryVectorStore, TopicRetriever
from .session import InterviewSessionEngine, QuestionPlanner, SessionStateError
from .benchmark import BenchmarkReport, ProviderBenchmark
from .provider_adapters import FasterWhisperSTT, OpenRouterLLM, PiperKokoroTTS
from .routing import FallbackRouter, ProviderFlags

__all__ = [
    "DeterministicEmbeddingProvider",
    "InMemoryVectorStore",
    "LocalDocumentParser",
    "TopicRetriever",
    "DocumentChunk",
    "DocumentSource",
    "InterviewMode",
    "InterviewSession",
    "InterviewSessionEngine",
    "QuestionPlan",
    "QuestionPlanner",
    "RetrievedEvidence",
    "SessionStateError",
    "SessionStatus",
    "Turn",
    "BenchmarkReport",
    "ProviderBenchmark",
    "FasterWhisperSTT",
    "OpenRouterLLM",
    "PiperKokoroTTS",
    "FallbackRouter",
    "ProviderFlags",
]
