"""Configuration seams and provider-independent fallback routing."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, Protocol, Sequence, TypeVar

from .contracts import CancellationToken, ErrorCode, HealthStatus, ProviderError


class HealthCapable(Protocol):
    """Bound for FallbackRouter generic: providers must expose health()."""

    async def health(self) -> HealthStatus: ...


T = TypeVar("T", bound="HealthCapable")


@dataclass(frozen=True, slots=True)
class ProviderFlags:
    """Feature flags controlling optional provider activation."""

    enable_local_stt: bool = True
    enable_local_tts: bool = True
    enable_hosted_llm: bool = False


class FallbackRouter(Generic[T]):
    """Try configured providers in order and preserve the final normalized error."""

    def __init__(self, providers: Sequence[T], operation: str) -> None:
        if not providers:
            raise ValueError("at least one provider is required")
        self.providers = tuple(providers)
        self.operation = operation

    async def run(self, call: Callable[[T, CancellationToken], Awaitable[object]], token: CancellationToken) -> object:
        """Call providers until one succeeds or all fail."""
        last_error: ProviderError | None = None
        for provider in self.providers:
            try:
                return await call(provider, token)
            except ProviderError as error:
                last_error = error
                if error.code in {ErrorCode.CANCELLED, ErrorCode.INVALID_REQUEST}:
                    raise
        raise last_error or ProviderError(ErrorCode.INTERNAL, f"{self.operation} has no usable provider")

    async def health(self) -> list[HealthStatus]:
        """Return each provider health result without hiding fallback readiness."""
        return [await provider.health() for provider in self.providers]
