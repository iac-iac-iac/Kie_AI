from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from kie_sidecar.models.settings import AppSettings


class SettingsRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def init(self, schema_path: Path) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        schema = schema_path.read_text(encoding="utf-8")
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(schema)
            await db.commit()

    async def get_app_settings(self) -> AppSettings:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT key, value FROM settings") as cursor:
                rows = await cursor.fetchall()
        if not rows:
            return AppSettings()
        data: dict[str, object] = {}
        for row in rows:
            key = row["key"]
            raw = row["value"]
            try:
                data[key] = json.loads(raw)
            except json.JSONDecodeError:
                data[key] = raw
        return AppSettings.model_validate(data)

    async def save_app_settings(self, settings: AppSettings) -> None:
        payload = settings.model_dump()
        async with aiosqlite.connect(self._db_path) as db:
            for key, value in payload.items():
                await db.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, json.dumps(value)),
                )
            await db.commit()

    async def patch_app_settings(self, patch: dict[str, object]) -> AppSettings:
        current = await self.get_app_settings()
        if "proxy" in patch and isinstance(patch["proxy"], dict):
            patch = {
                **patch,
                "proxy": current.proxy.model_copy(update=patch["proxy"]),
            }
        merged = current.model_copy(update=patch)
        await self.save_app_settings(merged)
        return merged
