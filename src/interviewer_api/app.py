"""FastAPI composition root for the deterministic local interview service."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from interviewer_domain.contracts import ErrorCode, ProviderError
from interviewer_domain.models import InterviewMode
from interviewer_domain.persistence import (
    FixedWindowRateLimiter,
    InMemoryAuthProvider,
    InMemoryPersistentDataStore,
    PersistenceService,
    UserIdentity,
)
from interviewer_domain.providers import InMemoryStorage
from interviewer_domain.transport import CreateSessionRequest, RestResourceCatalog

APP_VERSION = "0.9.0"


class CreateInterviewRequest(BaseModel):
    """Validated interview setup payload."""

    mode: str = Field(pattern="^(recruiter|technical)$")


class InterviewApplication:
    """Own injected local capabilities and expose application use cases."""

    def __init__(self) -> None:
        """Create a credential-free in-memory development composition."""
        self.data = InMemoryPersistentDataStore()
        self.persistence = PersistenceService(self.data, InMemoryStorage())
        self.auth = InMemoryAuthProvider({"dev-token": UserIdentity("local-user")})
        self.rate_limiter = FixedWindowRateLimiter(limit=60, window_seconds=60)

    async def user_id(self, token: str) -> str:
        """Resolve a bearer token without exposing token details."""
        try:
            return await self.auth.validate(token)
        except ProviderError as error:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "authentication required"
            ) from error


application = InterviewApplication()
app = FastAPI(title="AI Mock Interview API", version=APP_VERSION)


async def current_user(authorization: Annotated[str | None, Header()] = None) -> str:
    """Require the documented local bearer token boundary."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    user = await application.user_id(authorization.removeprefix("Bearer ").strip())
    if not application.rate_limiter.allow(user, datetime.now(timezone.utc)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate limit exceeded")
    return user


def _safe_error(error: ProviderError) -> HTTPException:
    """Map domain errors to stable HTTP responses without internal details."""
    code = {
        ErrorCode.INVALID_REQUEST: 400,
        ErrorCode.CONFLICT: 409,
        ErrorCode.UNAVAILABLE: 404,
    }.get(error.code, 500)
    return HTTPException(code, "request cannot be completed")


@app.get("/healthz")
async def health() -> dict[str, str]:
    """Return a liveness response without credentials or domain data."""
    return {"status": "ok"}


@app.get("/api/v1/health")
async def api_health() -> dict[str, str]:
    """Return the versioned health response."""
    return {"status": "ok", "version": APP_VERSION}


@app.get("/api/v1/version")
async def version() -> dict[str, str]:
    """Return the running API version."""
    return {"version": APP_VERSION}


@app.post("/api/v1/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: CreateInterviewRequest, user_id: Annotated[str, Depends(current_user)]
) -> dict[str, object]:
    """Create an owned interview resource through the persistence service."""
    record = application.persistence.create_interview(
        user_id, InterviewMode(payload.mode), datetime.now(timezone.utc)
    )
    response = RestResourceCatalog.create_session(
        CreateSessionRequest(user_id, payload.mode), record.id
    )
    result: dict[str, object] = {key: value for key, value in response.to_dict().items()}
    result.update({"status": record.status})
    return result


@app.get("/api/v1/history")
async def history(user_id: Annotated[str, Depends(current_user)]) -> dict[str, object]:
    """Return only non-expired interviews owned by the authenticated user."""
    return application.persistence.resource(user_id, "history").to_dict()


@app.get("/api/v1/sessions/{interview_id}/{view}")
async def resource(
    interview_id: UUID, view: str, user_id: Annotated[str, Depends(current_user)]
) -> dict[str, object]:
    """Return one authorized setup, active, replay, transcript, or results view."""
    if view not in {"setup", "active", "replay", "transcript", "results"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "resource not found")
    try:
        return application.persistence.resource(user_id, view, interview_id).to_dict()
    except ProviderError as error:
        raise _safe_error(error) from error


@app.post("/api/v1/sessions/{interview_id}/complete")
async def complete(
    interview_id: UUID, user_id: Annotated[str, Depends(current_user)]
) -> dict[str, str]:
    """Complete an owned interview using the real persistence record."""
    try:
        record = application.data.get_interview(user_id, interview_id)
        application.data.save_interview(replace(record, status="completed"))
        return {"id": str(interview_id), "status": "completed"}
    except ProviderError as error:
        raise _safe_error(error) from error
