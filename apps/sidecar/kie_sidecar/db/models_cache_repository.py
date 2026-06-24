from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ModelCacheRow:
    id: str
    category: str
    price_hint: str | None
    estimate_credits: float | None
    updated_at: str


class ModelsCacheRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def upsert(
        self,
        *,
        model_id: str,
        category: str,
        price_hint: str | None,
        estimate_credits: float | None,
        updated_at: str | None = None,
    ) -> None:
        ts = updated_at or _now()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO models_cache (id, category, price_hint, estimate_credits, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id, category) DO UPDATE SET
                    price_hint = excluded.price_hint,
                    estimate_credits = excluded.estimate_credits,
                    updated_at = excluded.updated_at
                """,
                (model_id, category, price_hint, estimate_credits, ts),
            )
            await db.commit()

    async def get(self, model_id: str, category: str) -> ModelCacheRow | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, category, price_hint, estimate_credits, updated_at
                FROM models_cache WHERE id = ? AND category = ?
                """,
                (model_id, category),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        return ModelCacheRow(
            id=row["id"],
            category=row["category"],
            price_hint=row["price_hint"],
            estimate_credits=row["estimate_credits"],
            updated_at=row["updated_at"],
        )

    async def list_all(self) -> list[ModelCacheRow]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, category, price_hint, estimate_credits, updated_at
                FROM models_cache ORDER BY category, id
                """
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            ModelCacheRow(
                id=row["id"],
                category=row["category"],
                price_hint=row["price_hint"],
                estimate_credits=row["estimate_credits"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def count(self) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM models_cache") as cursor:
                row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def latest_updated_at(self) -> str | None:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT MAX(updated_at) FROM models_cache"
            ) as cursor:
                row = await cursor.fetchone()
        if not row or row[0] is None:
            return None
        return str(row[0])
