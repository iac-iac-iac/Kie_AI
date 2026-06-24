from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from kie_sidecar.models.chat import ChatFolder, ChatSummary, ContentBlock, MessageRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _title_from_content(content: list[ContentBlock]) -> str:
    for block in content:
        if block.type == "text" and block.text:
            text = block.text.strip().replace("\n", " ")
            return text[:40] + ("…" if len(text) > 40 else "")
    return "New chat"


def _blocks_to_markdown(blocks: list[ContentBlock]) -> str:
    parts: list[str] = []
    for block in blocks:
        if block.type == "text" and block.text:
            parts.append(block.text)
        elif block.type == "image_url" and block.url:
            parts.append(f"![image]({block.url})")
        elif block.type == "tool_result" and block.content:
            parts.append(block.content)
    return "\n\n".join(parts)


def _role_heading(role: str) -> str:
    if role == "user":
        return "User"
    if role == "assistant":
        return "Assistant"
    return "Tool"


class ChatRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def list_folders(self) -> list[ChatFolder]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, name, sort_order, created_at FROM chat_folders ORDER BY sort_order, created_at"
            ) as cursor:
                rows = await cursor.fetchall()
        return [ChatFolder(**dict(row)) for row in rows]

    async def create_folder(self, name: str) -> ChatFolder:
        folder_id = str(uuid.uuid4())
        created_at = _now()
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM chat_folders"
            ) as cursor:
                row = await cursor.fetchone()
                sort_order = int(row[0]) if row else 0
            await db.execute(
                "INSERT INTO chat_folders (id, name, sort_order, created_at) VALUES (?, ?, ?, ?)",
                (folder_id, name, sort_order, created_at),
            )
            await db.commit()
        return ChatFolder(id=folder_id, name=name, sort_order=sort_order, created_at=created_at)

    async def update_folder(self, folder_id: str, name: str) -> ChatFolder | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "UPDATE chat_folders SET name = ? WHERE id = ?",
                (name.strip() or "Folder", folder_id),
            )
            await db.commit()
            if cursor.rowcount == 0:
                return None
            async with db.execute(
                "SELECT id, name, sort_order, created_at FROM chat_folders WHERE id = ?",
                (folder_id,),
            ) as row_cursor:
                row = await row_cursor.fetchone()
        return ChatFolder(**dict(row)) if row else None

    async def delete_folder(self, folder_id: str) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE chats SET folder_id = NULL WHERE folder_id = ?",
                (folder_id,),
            )
            cursor = await db.execute(
                "DELETE FROM chat_folders WHERE id = ?",
                (folder_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def list_chats(
        self,
        folder_id: str | None = None,
        q: str | None = None,
    ) -> list[ChatSummary]:
        query = "SELECT id, folder_id, title, model_id, created_at, updated_at FROM chats WHERE 1=1"
        params: list[object] = []
        if folder_id is not None:
            query += " AND folder_id = ?"
            params.append(folder_id)
        if q and q.strip():
            query += " AND title LIKE ? ESCAPE '\\'"
            params.append(f"%{q.strip()}%")
        query += " ORDER BY updated_at DESC"
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, tuple(params)) as cursor:
                rows = await cursor.fetchall()
        return [ChatSummary(**dict(row)) for row in rows]

    async def get_chat(self, chat_id: str) -> ChatSummary | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, folder_id, title, model_id, created_at, updated_at FROM chats WHERE id = ?",
                (chat_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return ChatSummary(**dict(row)) if row else None

    async def create_chat(
        self,
        model_id: str,
        title: str | None = None,
        folder_id: str | None = None,
    ) -> ChatSummary:
        chat_id = str(uuid.uuid4())
        now = _now()
        chat_title = title or "New chat"
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO chats (id, folder_id, title, model_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, folder_id, chat_title, model_id, now, now),
            )
            await db.commit()
        return ChatSummary(
            id=chat_id,
            folder_id=folder_id,
            title=chat_title,
            model_id=model_id,
            created_at=now,
            updated_at=now,
        )

    async def update_chat(
        self,
        chat_id: str,
        *,
        title: str | None = None,
        folder_id: str | None = None,
        model_id: str | None = None,
        clear_folder: bool = False,
    ) -> ChatSummary | None:
        chat = await self.get_chat(chat_id)
        if not chat:
            return None
        new_title = title if title is not None else chat.title
        new_folder = None if clear_folder else (folder_id if folder_id is not None else chat.folder_id)
        new_model = model_id if model_id is not None else chat.model_id
        now = _now()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE chats SET title = ?, folder_id = ?, model_id = ?, updated_at = ? WHERE id = ?",
                (new_title, new_folder, new_model, now, chat_id),
            )
            await db.commit()
        return ChatSummary(
            id=chat_id,
            folder_id=new_folder,
            title=new_title,
            model_id=new_model,
            created_at=chat.created_at,
            updated_at=now,
        )

    async def delete_chat(self, chat_id: str) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def list_messages(
        self,
        chat_id: str,
        q: str | None = None,
    ) -> list[MessageRecord]:
        query = (
            "SELECT id, chat_id, role, content_json, tokens_in, tokens_out, credits, created_at "
            "FROM messages WHERE chat_id = ?"
        )
        params: list[object] = [chat_id]
        if q and q.strip():
            query += " AND content_json LIKE ? ESCAPE '\\'"
            params.append(f"%{q.strip()}%")
        query += " ORDER BY created_at"
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, tuple(params)) as cursor:
                rows = await cursor.fetchall()
        return [_row_to_message(row) for row in rows]

    async def export_chat_markdown(self, chat_id: str) -> str | None:
        chat = await self.get_chat(chat_id)
        if not chat:
            return None
        messages = await self.list_messages(chat_id)
        lines = [
            f"# {chat.title}",
            "",
            f"Model: {chat.model_id}",
            f"Exported: {_now()}",
            "",
            "---",
            "",
        ]
        for msg in messages:
            heading = _role_heading(msg.role)
            body = _blocks_to_markdown(msg.content)
            if not body:
                continue
            lines.append(f"## {heading}")
            lines.append("")
            lines.append(body)
            if msg.role == "assistant" and msg.credits is not None:
                lines.append("")
                lines.append(f"*Credits: {msg.credits}*")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    async def get_message(self, message_id: str) -> MessageRecord | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, chat_id, role, content_json, tokens_in, tokens_out, credits, created_at "
                "FROM messages WHERE id = ?",
                (message_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return _row_to_message(row) if row else None

    async def add_message(
        self,
        chat_id: str,
        role: str,
        content: list[ContentBlock],
        *,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        credits: float | None = None,
    ) -> MessageRecord:
        message_id = str(uuid.uuid4())
        now = _now()
        content_json = json.dumps([b.model_dump(exclude_none=True) for b in content])
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO messages (id, chat_id, role, content_json, tokens_in, tokens_out, credits, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (message_id, chat_id, role, content_json, tokens_in, tokens_out, credits, now),
            )
            await db.execute(
                "UPDATE chats SET updated_at = ? WHERE id = ?",
                (now, chat_id),
            )
            if role == "user":
                count_cursor = await db.execute(
                    "SELECT COUNT(*) FROM messages WHERE chat_id = ? AND role = 'user'",
                    (chat_id,),
                )
                count_row = await count_cursor.fetchone()
                if count_row and count_row[0] == 1:
                    title = _title_from_content(content)
                    await db.execute(
                        "UPDATE chats SET title = ? WHERE id = ?",
                        (title, chat_id),
                    )
            await db.commit()
        return MessageRecord(
            id=message_id,
            chat_id=chat_id,
            role=role,  # type: ignore[arg-type]
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            credits=credits,
            created_at=now,
        )

    async def add_session_credits(self, credits: float) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE session_usage SET credits_spent = credits_spent + ? WHERE id = 1",
                (credits,),
            )
            await db.commit()

    async def get_session_spent(self) -> float:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT credits_spent FROM session_usage WHERE id = 1") as cursor:
                row = await cursor.fetchone()
        return float(row[0]) if row else 0.0

    async def reset_session(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE session_usage SET credits_spent = 0, started_at = datetime('now') WHERE id = 1",
            )
            await db.commit()


def _row_to_message(row: aiosqlite.Row) -> MessageRecord:
    raw = json.loads(row["content_json"])
    content = [ContentBlock.model_validate(item) for item in raw]
    return MessageRecord(
        id=row["id"],
        chat_id=row["chat_id"],
        role=row["role"],
        content=content,
        tokens_in=row["tokens_in"],
        tokens_out=row["tokens_out"],
        credits=row["credits"],
        created_at=row["created_at"],
    )
