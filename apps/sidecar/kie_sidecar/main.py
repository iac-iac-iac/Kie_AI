from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import shutil
import sqlite3
import tempfile

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from kie_sidecar.api import account, chats, events, generations, models, settings, system
from kie_sidecar.config import get_settings
from kie_sidecar.services.pricing import sync_pricing
from kie_sidecar.state import AppState, create_app_state

logger = structlog.get_logger()

PRICING_SYNC_INTERVAL_SEC = 24 * 60 * 60
PRICING_DIR = Path(__file__).resolve().parent.parent / "pricing"


def _client_is_local(request: Request) -> bool:
    if not request.client:
        return False
    host = request.client.host
    if host in {"127.0.0.1", "::1", "localhost", "testclient"}:
        return True
    header_host = request.headers.get("host", "").split(":")[0].lower()
    return header_host in {"127.0.0.1", "localhost", "::1"}


def _resolve_pricing_overrides(path_str: str) -> Path:
    path = Path(path_str).resolve()
    pricing_root = PRICING_DIR.resolve()
    if not str(path).startswith(str(pricing_root)):
        raise HTTPException(status_code=400, detail="overrides_path must be under pricing/")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="overrides file not found")
    return path


class HealthResponse(BaseModel):
    status: str
    has_api_key: bool
    version: str
    pricing_updated_at: str | None = None


class ReloadKeyRequest(BaseModel):
    api_key: str


class CheckpointDbResponse(BaseModel):
    snapshot_path: str


class SyncPricingRequest(BaseModel):
    overrides_path: str | None = None


class SyncPricingResponse(BaseModel):
    seeded: int
    overrides_applied: int
    latest_updated_at: str | None


def _checkpoint_database(db_path: Path) -> str:
    if not db_path.is_file():
        raise HTTPException(status_code=404, detail=f"Database not found: {db_path}")

    tmp = Path(tempfile.mkdtemp(prefix="kie-db-snapshot-"))
    snapshot = tmp / "kie.db"
    try:
        with sqlite3.connect(db_path) as source:
            source.execute("PRAGMA wal_checkpoint(FULL)")
            with sqlite3.connect(snapshot) as dest:
                source.backup(dest)
        return str(snapshot)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


async def _run_pricing_sync(state: AppState) -> None:
    try:
        result = await sync_pricing(state.models_cache_repo)
        logger.info("pricing_sync_completed", **result)
    except Exception:
        logger.exception("pricing_sync_failed")


async def _pricing_sync_loop(state: AppState, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=PRICING_SYNC_INTERVAL_SEC)
            break
        except asyncio.TimeoutError:
            await _run_pricing_sync(state)


@asynccontextmanager
async def lifespan(app: FastAPI):
    env_settings = get_settings()
    env_settings.ensure_dirs()
    state = create_app_state(env_settings)
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    await state.repo.init(schema_path)
    state.app_settings = await state.repo.get_app_settings()
    state._settings_ref[0] = state.app_settings
    await state.kie.reload_proxy(state.app_settings.proxy)
    await state.file_uploader.reload_proxy(state.app_settings.proxy)
    await state.media_downloader.reload_proxy(state.app_settings.proxy)
    app.state.app_state = state
    await _run_pricing_sync(state)
    pricing_stop = asyncio.Event()
    pricing_task = asyncio.create_task(_pricing_sync_loop(state, pricing_stop))
    state.task_poller.start()
    logger.info("sidecar_started", data_dir=str(env_settings.data_dir), has_key=bool(env_settings.api_key))
    try:
        yield
    finally:
        pricing_stop.set()
        pricing_task.cancel()
        try:
            await pricing_task
        except asyncio.CancelledError:
            pass
        await state.task_poller.stop()
        await state.media_downloader.close()
        await state.kie.close()
        await state.file_uploader.close()


app = FastAPI(title="Kie AI Sidecar", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://localhost:5173",
        "http://127.0.0.1:1420",
        "http://127.0.0.1:5173",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def restrict_internal_routes(request: Request, call_next):
    if request.url.path.startswith("/internal/") and not _client_is_local(request):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    return await call_next(request)

app.include_router(settings.router, prefix="/api/v1")
app.include_router(account.router, prefix="/api/v1")
app.include_router(chats.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(generations.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    state: AppState = request.app.state.app_state
    pricing_updated_at = await state.models_cache_repo.latest_updated_at()
    return HealthResponse(
        status="ok",
        has_api_key=bool(state.settings.api_key),
        version=app.version,
        pricing_updated_at=pricing_updated_at,
    )


@app.post("/internal/reload-api-key")
async def reload_api_key(request: Request, body: ReloadKeyRequest) -> HealthResponse:
    state: AppState = request.app.state.app_state
    state.settings.api_key = body.api_key.strip() or None
    state.kie.update_credentials(state.settings.api_key)
    state.file_uploader.update_credentials(state.settings.api_key)
    pricing_updated_at = await state.models_cache_repo.latest_updated_at()
    return HealthResponse(
        status="ok",
        has_api_key=bool(state.settings.api_key),
        version=app.version,
        pricing_updated_at=pricing_updated_at,
    )


@app.post("/internal/checkpoint-db", response_model=CheckpointDbResponse)
async def checkpoint_db(request: Request) -> CheckpointDbResponse:
    state: AppState = request.app.state.app_state
    snapshot_path = _checkpoint_database(state.settings.db_path)
    return CheckpointDbResponse(snapshot_path=snapshot_path)


@app.post("/internal/sync-pricing", response_model=SyncPricingResponse)
async def sync_pricing_endpoint(
    request: Request,
    body: SyncPricingRequest | None = None,
) -> SyncPricingResponse:
    state: AppState = request.app.state.app_state
    overrides_path = (
        _resolve_pricing_overrides(body.overrides_path)
        if body and body.overrides_path
        else None
    )
    result = await sync_pricing(state.models_cache_repo, overrides_path)
    return SyncPricingResponse(
        seeded=int(result["seeded"]),
        overrides_applied=int(result["overrides_applied"]),
        latest_updated_at=result["latest_updated_at"],  # type: ignore[arg-type]
    )
