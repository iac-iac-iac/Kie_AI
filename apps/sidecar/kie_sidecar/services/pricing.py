from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from kie_sidecar.db.models_cache_repository import ModelCacheRow, ModelsCacheRepository
from kie_sidecar.models.registry import (
    AudioModelDefinition,
    ChatModelDefinition,
    ImageModelDefinition,
    VideoModelDefinition,
    get_audio_models,
    get_chat_models,
    get_image_models,
    get_video_models,
)

DEFAULT_OVERRIDES_PATH = (
    Path(__file__).resolve().parents[2] / "pricing" / "pricing_overrides.json"
)

RegistryModel = ChatModelDefinition | ImageModelDefinition | VideoModelDefinition | AudioModelDefinition


@dataclass(frozen=True)
class MergedPricing:
    price_hint: str
    estimate_credits: float | None
    price_updated_at: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def merge_pricing(
    registry_price_hint: str,
    registry_estimate: float | None,
    cache_row: ModelCacheRow | None,
) -> MergedPricing:
    if cache_row is None:
        return MergedPricing(
            price_hint=registry_price_hint,
            estimate_credits=registry_estimate,
            price_updated_at=None,
        )
    return MergedPricing(
        price_hint=cache_row.price_hint or registry_price_hint,
        estimate_credits=(
            cache_row.estimate_credits
            if cache_row.estimate_credits is not None
            else registry_estimate
        ),
        price_updated_at=cache_row.updated_at,
    )


async def seed_from_registry(repo: ModelsCacheRepository) -> int:
    if await repo.count() > 0:
        return 0

    ts = _now()
    count = 0
    for model in get_chat_models():
        await repo.upsert(
            model_id=model.id,
            category="chat",
            price_hint=model.price_hint,
            estimate_credits=model.estimate_credits,
            updated_at=ts,
        )
        count += 1
    for model in get_image_models():
        await repo.upsert(
            model_id=model.id,
            category="image",
            price_hint=model.price_hint,
            estimate_credits=model.estimate_credits,
            updated_at=ts,
        )
        count += 1
    for model in get_video_models():
        await repo.upsert(
            model_id=model.id,
            category="video",
            price_hint=model.price_hint,
            estimate_credits=model.estimate_credits,
            updated_at=ts,
        )
        count += 1
    for model in get_audio_models():
        await repo.upsert(
            model_id=model.id,
            category="audio",
            price_hint=model.price_hint,
            estimate_credits=model.estimate_credits,
            updated_at=ts,
        )
        count += 1
    return count


async def apply_overrides(
    repo: ModelsCacheRepository,
    overrides_path: Path | None = None,
) -> int:
    path = overrides_path or DEFAULT_OVERRIDES_PATH
    if not path.is_file():
        return 0

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("pricing_overrides.json must be a JSON array")

    ts = _now()
    count = 0
    for item in raw:
        model_id = item.get("id")
        category = item.get("category")
        if not model_id or not category:
            continue
        await repo.upsert(
            model_id=str(model_id),
            category=str(category),
            price_hint=item.get("price_hint"),
            estimate_credits=item.get("estimate_credits"),
            updated_at=ts,
        )
        count += 1
    return count


async def sync_pricing(
    repo: ModelsCacheRepository,
    overrides_path: Path | None = None,
) -> dict[str, int | str | None]:
    seeded = await seed_from_registry(repo)
    applied = await apply_overrides(repo, overrides_path)
    latest = await repo.latest_updated_at()
    return {
        "seeded": seeded,
        "overrides_applied": applied,
        "latest_updated_at": latest,
    }


async def get_merged_pricing(
    repo: ModelsCacheRepository,
    model: RegistryModel,
    category: Literal["chat", "image", "video", "audio"],
) -> MergedPricing:
    cache_row = await repo.get(model.id, category)
    return merge_pricing(model.price_hint, model.estimate_credits, cache_row)
