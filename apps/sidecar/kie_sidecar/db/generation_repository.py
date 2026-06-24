from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import aiosqlite

GenerationStatus = Literal["pending", "running", "success", "failed"]
GenerationType = Literal["image", "video", "audio"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GenerationRecord:
    def __init__(
        self,
        id: str,
        type: GenerationType,
        model_id: str,
        task_id: str | None,
        status: GenerationStatus,
        prompt: str | None,
        params: dict[str, Any] | None,
        credits_used: float | None,
        remote_url: str | None,
        local_path: str | None,
        error_msg: str | None,
        created_at: str,
        completed_at: str | None,
    ) -> None:
        self.id = id
        self.type = type
        self.model_id = model_id
        self.task_id = task_id
        self.status = status
        self.prompt = prompt
        self.params = params
        self.credits_used = credits_used
        self.remote_url = remote_url
        self.local_path = local_path
        self.error_msg = error_msg
        self.created_at = created_at
        self.completed_at = completed_at


def _row_to_record(row: aiosqlite.Row) -> GenerationRecord:
    params = json.loads(row["params_json"]) if row["params_json"] else None
    return GenerationRecord(
        id=row["id"],
        type=row["type"],
        model_id=row["model_id"],
        task_id=row["task_id"],
        status=row["status"],
        prompt=row["prompt"],
        params=params,
        credits_used=row["credits_used"],
        remote_url=row["remote_url"],
        local_path=row["local_path"],
        error_msg=row["error_msg"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


class GenerationRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def create_generation(
        self,
        *,
        type: GenerationType,
        model_id: str,
        task_id: str | None,
        prompt: str | None,
        params: dict[str, Any] | None,
        status: GenerationStatus = "pending",
    ) -> GenerationRecord:
        generation_id = str(uuid.uuid4())
        created_at = _now()
        params_json = json.dumps(params) if params else None
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO generations (
                    id, type, model_id, task_id, status, prompt, params_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    type,
                    model_id,
                    task_id,
                    status,
                    prompt,
                    params_json,
                    created_at,
                ),
            )
            await db.commit()
        return GenerationRecord(
            id=generation_id,
            type=type,
            model_id=model_id,
            task_id=task_id,
            status=status,
            prompt=prompt,
            params=params,
            credits_used=None,
            remote_url=None,
            local_path=None,
            error_msg=None,
            created_at=created_at,
            completed_at=None,
        )

    async def get_generation(self, generation_id: str) -> GenerationRecord | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM generations WHERE id = ?",
                (generation_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return _row_to_record(row) if row else None

    async def list_generations(self, type: GenerationType | None = None) -> list[GenerationRecord]:
        query = "SELECT * FROM generations"
        params: tuple[object, ...] = ()
        if type is not None:
            query += " WHERE type = ?"
            params = (type,)
        query += " ORDER BY created_at DESC"
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        return [_row_to_record(row) for row in rows]

    async def list_pending(self) -> list[GenerationRecord]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM generations
                WHERE status IN ('pending', 'running')
                ORDER BY created_at ASC
                """
            ) as cursor:
                rows = await cursor.fetchall()
        return [_row_to_record(row) for row in rows]

    async def update_status(
        self,
        generation_id: str,
        *,
        status: GenerationStatus,
        task_id: str | None = None,
        credits_used: float | None = None,
        remote_url: str | None = None,
        local_path: str | None = None,
        error_msg: str | None = None,
    ) -> GenerationRecord | None:
        completed_at = _now() if status in ("success", "failed") else None
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            fields: list[str] = ["status = ?"]
            values: list[object] = [status]
            if task_id is not None:
                fields.append("task_id = ?")
                values.append(task_id)
            if credits_used is not None:
                fields.append("credits_used = ?")
                values.append(credits_used)
            if remote_url is not None:
                fields.append("remote_url = ?")
                values.append(remote_url)
            if local_path is not None:
                fields.append("local_path = ?")
                values.append(local_path)
            if error_msg is not None:
                fields.append("error_msg = ?")
                values.append(error_msg)
            if completed_at is not None:
                fields.append("completed_at = ?")
                values.append(completed_at)
            values.append(generation_id)
            await db.execute(
                f"UPDATE generations SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM generations WHERE id = ?",
                (generation_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return _row_to_record(row) if row else None

    async def requeue_generation(self, generation_id: str) -> GenerationRecord | None:
        record = await self.get_generation(generation_id)
        if not record or not record.task_id:
            return None
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE generations
                SET status = 'pending', error_msg = NULL, completed_at = NULL
                WHERE id = ?
                """,
                (generation_id,),
            )
            await db.commit()
        return await self.get_generation(generation_id)

    async def delete_generation(self, generation_id: str) -> GenerationRecord | None:
        record = await self.get_generation(generation_id)
        if not record:
            return None
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM generations WHERE id = ?", (generation_id,))
            await db.commit()
        return record
