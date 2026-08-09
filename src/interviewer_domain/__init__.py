"""Domain and capability foundation for the voice-first interview platform."""

from .benchmark import BenchmarkReport, ProviderBenchmark
from .documents import LocalDocumentParser
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
from .provider_adapters import FasterWhisperSTT, OpenRouterLLM, PiperKokoroTTS
from .retrieval import (
    DeterministicEmbeddingProvider,
    InMemoryVectorStore,
    TopicRetriever,
)
from .routing import FallbackRouter, ProviderFlags
from .session import InterviewSessionEngine, QuestionPlanner, SessionStateError
from .transport import (
    BrowserControlTransport,
    BrowserMediaTransport,
    CreateSessionRequest,
    LocalBrowserControlTransport,
    LocalSessionEventChannel,
    LocalWebRTCMediaTransport,
    RestResourceCatalog,
    SessionEvent,
    SessionEventType,
    SessionResponse,
    SignalingMessage,
    SignalingType,
    TransportValidationError,
)

__all__ = [
    "BenchmarkReport",
    "BrowserControlTransport",
    "BrowserMediaTransport",
    "CreateSessionRequest",
    "DeterministicEmbeddingProvider",
    "DocumentChunk",
    "DocumentSource",
    "FallbackRouter",
    "FasterWhisperSTT",
    "InMemoryVectorStore",
    "InterviewMode",
    "InterviewSession",
    "InterviewSessionEngine",
    "LocalBrowserControlTransport",
    "LocalDocumentParser",
    "LocalSessionEventChannel",
    "LocalWebRTCMediaTransport",
    "OpenRouterLLM",
    "PiperKokoroTTS",
    "ProviderBenchmark",
    "ProviderFlags",
    "QuestionPlan",
    "QuestionPlanner",
    "RestResourceCatalog",
    "RetrievedEvidence",
    "SessionEvent",
    "SessionEventType",
    "SessionResponse",
    "SessionStateError",
    "SessionStatus",
    "SignalingMessage",
    "SignalingType",
    "TopicRetriever",
    "TransportValidationError",
    "Turn",
]
