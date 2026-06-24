from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from kie_sidecar.kie.errors import KieApiError, KieAuthError
from kie_sidecar.services.session_limits import get_usage, record_spent, reset_session

router = APIRouter(prefix="/account", tags=["account"])


class CreditsResponse(BaseModel):
    credits: float


class TestConnectionResponse(BaseModel):
    ok: bool
    credits: float | None = None
    error: str | None = None


class SessionUsageResponse(BaseModel):
    spent: float
    limit: float | None
    remaining: float | None


@router.get("/credits", response_model=CreditsResponse)
async def get_credits(request: Request) -> CreditsResponse:
    state = request.app.state.app_state
    if not state.settings.api_key:
        raise HTTPException(status_code=401, detail="API key is not configured")
    try:
        credits = await state.kie.get_credits()
    except KieAuthError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc
    except KieApiError as exc:
        raise HTTPException(status_code=exc.code, detail=exc.message) from exc
    return CreditsResponse(credits=credits)


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(request: Request) -> TestConnectionResponse:
    state = request.app.state.app_state
    if not state.settings.api_key:
        return TestConnectionResponse(ok=False, error="invalid_key")
    try:
        credits = await state.kie.get_credits()
        return TestConnectionResponse(ok=True, credits=credits)
    except KieAuthError:
        return TestConnectionResponse(ok=False, error="invalid_key")
    except KieApiError as exc:
        return TestConnectionResponse(ok=False, error=exc.message)


@router.get("/session-usage", response_model=SessionUsageResponse)
async def get_session_usage(request: Request) -> SessionUsageResponse:
    state = request.app.state.app_state
    usage = await get_usage(state.chat_repo, state.app_settings)
    return SessionUsageResponse(spent=usage.spent, limit=usage.limit, remaining=usage.remaining)


@router.post("/reset-session", status_code=204)
async def reset_session_usage(request: Request) -> None:
    state = request.app.state.app_state
    await reset_session(state.chat_repo)
