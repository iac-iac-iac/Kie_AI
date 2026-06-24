from __future__ import annotations

from pathlib import Path

import pytest

from kie_sidecar.db.models_cache_repository import ModelsCacheRepository
from kie_sidecar.services.pricing import apply_overrides, merge_pricing, seed_from_registry, sync_pricing
from kie_sidecar.db.models_cache_repository import ModelCacheRow


@pytest.mark.asyncio
async def test_merge_pricing_uses_cache_when_present():
    merged = merge_pricing(
        "~25 кр.",
        25.0,
        ModelCacheRow(
            id="flux-test",
            category="image",
            price_hint="~30 кр.",
            estimate_credits=30.0,
            updated_at="2026-06-22T12:00:00+00:00",
        ),
    )
    assert merged.price_hint == "~30 кр."
    assert merged.estimate_credits == 30.0
    assert merged.price_updated_at == "2026-06-22T12:00:00+00:00"


@pytest.mark.asyncio
async def test_merge_pricing_falls_back_to_registry(tmp_path: Path):
    merged = merge_pricing("~10 кр.", 10.0, None)
    assert merged.price_hint == "~10 кр."
    assert merged.estimate_credits == 10.0
    assert merged.price_updated_at is None


@pytest.mark.asyncio
async def test_seed_and_apply_overrides(tmp_path: Path):
    db_path = tmp_path / "kie.db"
    schema = Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"
    async with __import__("aiosqlite").connect(db_path) as db:
        await db.executescript(schema.read_text(encoding="utf-8"))
        await db.commit()

    repo = ModelsCacheRepository(db_path)
    seeded = await seed_from_registry(repo)
    assert seeded > 0
    assert await repo.count() > 0

    overrides = tmp_path / "overrides.json"
    overrides.write_text(
        '[{"id": "flux-2/pro-text-to-image", "category": "image", '
        '"price_hint": "~99 кр.", "estimate_credits": 99}]',
        encoding="utf-8",
    )
    applied = await apply_overrides(repo, overrides)
    assert applied == 1

    row = await repo.get("flux-2/pro-text-to-image", "image")
    assert row is not None
    assert row.price_hint == "~99 кр."
    assert row.estimate_credits == 99.0


@pytest.mark.asyncio
async def test_sync_pricing_idempotent_seed(tmp_path: Path):
    db_path = tmp_path / "kie.db"
    schema = Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"
    async with __import__("aiosqlite").connect(db_path) as db:
        await db.executescript(schema.read_text(encoding="utf-8"))
        await db.commit()

    repo = ModelsCacheRepository(db_path)
    first = await sync_pricing(repo)
    second = await sync_pricing(repo)
    assert first["seeded"] > 0
    assert second["seeded"] == 0
