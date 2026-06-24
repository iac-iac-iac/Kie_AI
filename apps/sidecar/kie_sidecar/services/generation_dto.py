from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from kie_sidecar.models.generation import GenerationRecord

if TYPE_CHECKING:
    from kie_sidecar.db.generation_repository import GenerationRecord as DbGenerationRecord


def generation_to_dto(record: DbGenerationRecord) -> GenerationRecord:
    return GenerationRecord(
        id=record.id,
        type=record.type,
        model_id=record.model_id,
        task_id=record.task_id,
        status=record.status,
        prompt=record.prompt,
        params=record.params,
        credits_used=record.credits_used,
        remote_url=record.remote_url,
        local_path=record.local_path,
        error_msg=record.error_msg,
        created_at=record.created_at,
        completed_at=record.completed_at,
        has_file=bool(record.local_path and Path(record.local_path).exists()),
    )


def generation_to_event_data(record: DbGenerationRecord) -> dict:
    return generation_to_dto(record).model_dump()
