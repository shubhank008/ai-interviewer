"""Typed runtime configuration and provider readiness composition."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from .contracts import (
    CapabilityDescriptor,
    HealthStatus,
    LLMProvider,
    STTProvider,
    TTSProvider,
)
from .provider_adapters import (
    FasterWhisperSTT,
    OpenRouterLLM,
    OpenRouterTransport,
    PiperKokoroTTS,
    SpeechBackend,
    WhisperBackend,
)
from .providers import InMemoryLLM, InMemorySTT, InMemoryTTS
from .routing import FallbackRouter


class ConfigurationError(ValueError):
    """Raised when runtime configuration cannot safely compose the service."""


class RuntimeProfile(StrEnum):
    """Supported runtime behavior profiles."""

    LOCAL = "local"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Validated, provider-neutral settings loaded from environment variables."""

    profile: RuntimeProfile
    firebase_project_id: str | None
    firebase_auth_domain: str | None
    firebase_api_key: str | None
    firestore_database: str | None
    storage_backend: str
    storage_bucket: str | None
    storage_path: str
    stt_provider: str
    stt_fallback_provider: str
    stt_api_key: str | None
    stt_model: str
    tts_provider: str
    tts_fallback_provider: str
    tts_api_key: str | None
    tts_model: str
    llm_provider: str
    llm_fallback_provider: str
    llm_api_key: str | None
    llm_model: str
    webrtc_ice_servers: str
    webrtc_sample_rate: int
    cors_origins: tuple[str, ...]
    retention_days: int
    rate_limit: int
    rate_window_seconds: int
    health_timeout_seconds: float
    log_level: str
    metrics_enabled: bool
    tracing_enabled: bool

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "RuntimeSettings":
        """Load and validate settings without reading secrets into diagnostics."""
        values = environ if environ is not None else os.environ
        try:
            profile = RuntimeProfile(
                values.get("APP_PROFILE", RuntimeProfile.LOCAL.value).lower()
            )
        except ValueError as exc:
            raise ConfigurationError("APP_PROFILE has an unsupported value") from exc
        settings = cls(
            profile=profile,
            firebase_project_id=_optional(values, "FIREBASE_PROJECT_ID"),
            firebase_auth_domain=_optional(values, "FIREBASE_AUTH_DOMAIN"),
            firebase_api_key=_optional(values, "FIREBASE_API_KEY"),
            firestore_database=_optional(values, "FIRESTORE_DATABASE"),
            storage_backend=values.get("STORAGE_BACKEND", "local"),
            storage_bucket=_optional(values, "STORAGE_BUCKET"),
            storage_path=values.get("STORAGE_PATH", "./var/storage"),
            stt_provider=values.get("STT_PROVIDER", "in-memory"),
            stt_fallback_provider=values.get("STT_FALLBACK_PROVIDER", "in-memory"),
            stt_api_key=_optional(values, "STT_API_KEY"),
            stt_model=values.get("STT_MODEL", "base.en"),
            tts_provider=values.get("TTS_PROVIDER", "in-memory"),
            tts_fallback_provider=values.get("TTS_FALLBACK_PROVIDER", "in-memory"),
            tts_api_key=_optional(values, "TTS_API_KEY"),
            tts_model=values.get("TTS_MODEL", "default"),
            llm_provider=values.get("LLM_PROVIDER", "in-memory"),
            llm_fallback_provider=values.get("LLM_FALLBACK_PROVIDER", "in-memory"),
            llm_api_key=_optional(values, "LLM_API_KEY"),
            llm_model=values.get("LLM_MODEL", "default"),
            webrtc_ice_servers=values.get(
                "WEBRTC_ICE_SERVERS", "stun:stun.l.google.com:19302"
            ),
            webrtc_sample_rate=_integer(
                values, "WEBRTC_SAMPLE_RATE", 48000, minimum=8000
            ),
            cors_origins=_csv(values.get("CORS_ORIGINS", "http://localhost:5173")),
            retention_days=_integer(values, "RETENTION_DAYS", 14, minimum=1),
            rate_limit=_integer(values, "RATE_LIMIT", 60, minimum=1),
            rate_window_seconds=_integer(values, "RATE_WINDOW_SECONDS", 60, minimum=1),
            health_timeout_seconds=_number(
                values, "HEALTH_TIMEOUT_SECONDS", 2.0, minimum=0.1
            ),
            log_level=values.get("LOG_LEVEL", "INFO").upper(),
            metrics_enabled=_boolean(values, "METRICS_ENABLED", False),
            tracing_enabled=_boolean(values, "TRACING_ENABLED", False),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Reject unsafe values and missing production requirements."""
        if self.storage_backend not in {"local", "s3", "gcs"}:
            raise ConfigurationError("STORAGE_BACKEND must be local, s3, or gcs")
        if self.profile is RuntimeProfile.LOCAL:
            return
        required = {
            "FIREBASE_PROJECT_ID": self.firebase_project_id,
            "FIRESTORE_DATABASE": self.firestore_database,
            "STT_PROVIDER": self.stt_provider,
            "TTS_PROVIDER": self.tts_provider,
            "LLM_PROVIDER": self.llm_provider,
        }
        missing = [
            name
            for name, value in required.items()
            if not value or value == "in-memory"
        ]
        if self.storage_backend != "local" and not self.storage_bucket:
            missing.append("STORAGE_BUCKET")
        if self.stt_provider in {"groq", "hosted"} and not self.stt_api_key:
            missing.append("STT_API_KEY")
        if self.tts_provider in {"hosted"} and not self.tts_api_key:
            missing.append("TTS_API_KEY")
        if self.llm_provider in {"openrouter", "hosted"} and not self.llm_api_key:
            missing.append("LLM_API_KEY")
        if missing:
            raise ConfigurationError(
                "production configuration is missing: "
                + ", ".join(sorted(set(missing)))
            )
        recognized_stt = {"faster-whisper", "in-memory"}
        recognized_tts = {"piper", "kokoro", "in-memory"}
        recognized_llm = {"openrouter", "in-memory"}
        if self.stt_provider not in recognized_stt:
            raise ConfigurationError(
                f"STT_PROVIDER must be one of {sorted(recognized_stt)}"
            )
        if self.tts_provider not in recognized_tts:
            raise ConfigurationError(
                f"TTS_PROVIDER must be one of {sorted(recognized_tts)}"
            )
        if self.llm_provider not in recognized_llm:
            raise ConfigurationError(
                f"LLM_PROVIDER must be one of {sorted(recognized_llm)}"
            )
        if self.stt_fallback_provider not in recognized_stt:
            raise ConfigurationError(
                f"STT_FALLBACK_PROVIDER must be one of {sorted(recognized_stt)}"
            )
        if self.tts_fallback_provider not in recognized_tts:
            raise ConfigurationError(
                f"TTS_FALLBACK_PROVIDER must be one of {sorted(recognized_tts)}"
            )
        if self.llm_fallback_provider not in recognized_llm:
            raise ConfigurationError(
                f"LLM_FALLBACK_PROVIDER must be one of {sorted(recognized_llm)}"
            )

    def diagnostics(self) -> dict[str, object]:
        """Return safe startup details with secret values represented only by presence."""
        return {
            "profile": self.profile.value,
            "providers": {
                "stt": self.stt_provider,
                "tts": self.tts_provider,
                "llm": self.llm_provider,
            },
            "fallbacks": {
                "stt": self.stt_fallback_provider,
                "tts": self.tts_fallback_provider,
                "llm": self.llm_fallback_provider,
            },
            "storage_backend": self.storage_backend,
            "firebase_configured": bool(self.firebase_project_id),
            "secrets_configured": {
                "firebase_api_key": bool(self.firebase_api_key),
                "stt_api_key": bool(self.stt_api_key),
                "tts_api_key": bool(self.tts_api_key),
                "llm_api_key": bool(self.llm_api_key),
            },
            "retention_days": self.retention_days,
            "rate_limit": self.rate_limit,
            "rate_window_seconds": self.rate_window_seconds,
            "cors_origins": self.cors_origins,
        }


@dataclass(frozen=True, slots=True)
class ProviderBackends:
    """Optional injected seams for provider-shaped production adapters."""

    stt: WhisperBackend | None = None
    tts: SpeechBackend | None = None
    llm: OpenRouterTransport | None = None


@dataclass(frozen=True, slots=True)
class RuntimeProviders:
    """Ordered capability providers selected by the active runtime profile."""

    stt: tuple[STTProvider, ...]
    tts: tuple[TTSProvider, ...]
    llm: tuple[LLMProvider, ...]

    def routers(
        self,
    ) -> tuple[
        FallbackRouter[STTProvider],
        FallbackRouter[TTSProvider],
        FallbackRouter[LLMProvider],
    ]:
        """Create independent ordered fallback routers for the three voice capabilities."""
        return (
            FallbackRouter(self.stt, "stt"),
            FallbackRouter(self.tts, "tts"),
            FallbackRouter(self.llm, "llm"),
        )


def compose_providers(
    settings: RuntimeSettings, backends: ProviderBackends | None = None
) -> RuntimeProviders:
    """Compose deterministic local or injected provider-shaped implementations."""
    injected = backends or ProviderBackends()
    if settings.profile is RuntimeProfile.LOCAL:
        return RuntimeProviders((InMemorySTT(),), (InMemoryTTS(),), (InMemoryLLM(),))
    stt: STTProvider = (
        FasterWhisperSTT(injected.stt, settings.stt_model)
        if settings.stt_provider == "faster-whisper"
        else InMemorySTT()
    )
    tts: TTSProvider = (
        PiperKokoroTTS(injected.tts, settings.tts_model)
        if settings.tts_provider in {"piper", "kokoro"}
        else InMemoryTTS()
    )
    llm: LLMProvider = (
        OpenRouterLLM(injected.llm, settings.llm_api_key, settings.llm_model)
        if settings.llm_provider == "openrouter"
        else InMemoryLLM()
    )
    return RuntimeProviders(
        (stt, _fallback_stt(settings, injected)),
        (tts, _fallback_tts(settings, injected)),
        (llm, _fallback_llm(settings, injected)),
    )


def _fallback_stt(settings: RuntimeSettings, backends: ProviderBackends) -> STTProvider:
    """Build the configured STT fallback without importing optional dependencies."""
    return (
        FasterWhisperSTT(backends.stt, settings.stt_model)
        if settings.stt_fallback_provider == "faster-whisper"
        else InMemorySTT()
    )


def _fallback_tts(settings: RuntimeSettings, backends: ProviderBackends) -> TTSProvider:
    """Build the configured TTS fallback without importing optional dependencies."""
    return (
        PiperKokoroTTS(backends.tts, settings.tts_model)
        if settings.tts_fallback_provider in {"piper", "kokoro"}
        else InMemoryTTS()
    )


def _fallback_llm(settings: RuntimeSettings, backends: ProviderBackends) -> LLMProvider:
    """Build the configured LLM fallback without importing optional dependencies."""
    return (
        OpenRouterLLM(backends.llm, settings.llm_api_key, settings.llm_model)
        if settings.llm_fallback_provider == "openrouter"
        else InMemoryLLM()
    )


@dataclass(frozen=True, slots=True)
class CapabilityReadiness:
    """Normalized health and capability report for one provider chain."""

    capability: str
    statuses: tuple[HealthStatus, ...]
    descriptors: tuple[CapabilityDescriptor, ...]
    required: bool

    @property
    def healthy(self) -> bool:
        """Return whether at least one provider in the chain is healthy."""
        return any(status.healthy for status in self.statuses)


class ProviderReadinessChecker:
    """Check configured provider chains without making network calls itself."""

    def __init__(self, providers: RuntimeProviders, required: bool = False) -> None:
        self.providers = providers
        self.required = required

    async def check(self) -> tuple[CapabilityReadiness, ...]:
        """Collect health and capability data for STT, TTS, and LLM chains."""
        reports: list[CapabilityReadiness] = []
        for name, chain in (
            ("stt", self.providers.stt),
            ("tts", self.providers.tts),
            ("llm", self.providers.llm),
        ):
            statuses = tuple([await provider.health() for provider in chain])
            descriptors = tuple(provider.capabilities() for provider in chain)
            report = CapabilityReadiness(name, statuses, descriptors, self.required)
            if self.required and not report.healthy:
                raise ConfigurationError(f"required {name} capability is not healthy")
            reports.append(report)
        return tuple(reports)


def _optional(values: Mapping[str, str], name: str) -> str | None:
    """Return a trimmed optional environment value."""
    value = values.get(name, "").strip()
    return value or None


def _integer(values: Mapping[str, str], name: str, default: int, minimum: int) -> int:
    """Parse a bounded integer setting."""
    try:
        result = int(values.get(name, str(default)))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if result < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return result


def _number(
    values: Mapping[str, str], name: str, default: float, minimum: float
) -> float:
    """Parse a bounded floating-point setting."""
    try:
        result = float(values.get(name, str(default)))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be numeric") from exc
    if result < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return result


def _boolean(values: Mapping[str, str], name: str, default: bool) -> bool:
    """Parse an explicit boolean setting."""
    value = values.get(name, str(default)).lower()
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise ConfigurationError(f"{name} must be boolean")
    return value in {"true", "1", "yes"}


def _csv(value: str) -> tuple[str, ...]:
    """Normalize comma-separated origins while preserving order."""
    return tuple(item.strip() for item in value.split(",") if item.strip())
