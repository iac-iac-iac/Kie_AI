from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from kie_sidecar.kie.chat import ChatStreamer, StreamDelta, StreamDone, StreamError
from kie_sidecar.kie.errors import KieApiError, KieAuthError, KieInsufficientCreditsError
from kie_sidecar.models.chat import (
    ChatFolder,
    ChatModelInfo,
    ChatSummary,
    ContentBlock,
    CreateChatRequest,
    CreateFolderRequest,
    MessageRecord,
    SendMessageRequest,
    SendMessageResponse,
    UpdateChatRequest,
    UpdateFolderRequest,
    UploadResponse,
)
from kie_sidecar.models.registry import get_chat_model, get_chat_models
from kie_sidecar.services.pricing import get_merged_pricing
from kie_sidecar.services.session_limits import SessionLimitExceeded, check_can_spend, record_spent

router = APIRouter(prefix="/chats", tags=["chats"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/models", response_model=list[ChatModelInfo])
async def list_chat_models(request: Request) -> list[ChatModelInfo]:
    state = request.app.state.app_state
    result: list[ChatModelInfo] = []
    for m in get_chat_models():
        pricing = await get_merged_pricing(state.models_cache_repo, m, "chat")
        result.append(
            ChatModelInfo(
                id=m.id,
                display_name=m.display_name,
                price_hint=pricing.price_hint,
                estimate_credits=pricing.estimate_credits,
                price_updated_at=pricing.price_updated_at,
                supports_vision=m.supports_vision,
                supports_tools=m.supports_tools,
            )
        )
    return result


@router.get("/folders", response_model=list[ChatFolder])
async def list_folders(request: Request) -> list[ChatFolder]:
    state = request.app.state.app_state
    return await state.chat_repo.list_folders()


@router.post("/folders", response_model=ChatFolder)
async def create_folder(request: Request, body: CreateFolderRequest) -> ChatFolder:
    state = request.app.state.app_state
    return await state.chat_repo.create_folder(body.name.strip() or "Folder")


@router.patch("/folders/{folder_id}", response_model=ChatFolder)
async def update_folder(
    request: Request,
    folder_id: str,
    body: UpdateFolderRequest,
) -> ChatFolder:
    state = request.app.state.app_state
    folder = await state.chat_repo.update_folder(folder_id, body.name)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(request: Request, folder_id: str) -> None:
    state = request.app.state.app_state
    deleted = await state.chat_repo.delete_folder(folder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")


@router.get("", response_model=list[ChatSummary])
async def list_chats(
    request: Request,
    folder_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[ChatSummary]:
    state = request.app.state.app_state
    return await state.chat_repo.list_chats(folder_id=folder_id, q=q)


@router.post("", response_model=ChatSummary)
async def create_chat(request: Request, body: CreateChatRequest) -> ChatSummary:
    state = request.app.state.app_state
    if not get_chat_model(body.model_id):
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model_id}")
    return await state.chat_repo.create_chat(
        model_id=body.model_id,
        title=body.title,
        folder_id=body.folder_id,
    )


@router.patch("/{chat_id}", response_model=ChatSummary)
async def update_chat(
    request: Request,
    chat_id: str,
    body: UpdateChatRequest,
) -> ChatSummary:
    state = request.app.state.app_state
    clear_folder = "folder_id" in body.model_fields_set and body.folder_id is None
    chat = await state.chat_repo.update_chat(
        chat_id,
        title=body.title,
        folder_id=body.folder_id,
        model_id=body.model_id,
        clear_folder=clear_folder,
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(request: Request, chat_id: str) -> None:
    state = request.app.state.app_state
    deleted = await state.chat_repo.delete_chat(chat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.get("/{chat_id}/export")
async def export_chat(request: Request, chat_id: str) -> Response:
    state = request.app.state.app_state
    markdown = await state.chat_repo.export_chat_markdown(chat_id)
    if markdown is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat = await state.chat_repo.get_chat(chat_id)
    assert chat is not None
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in chat.title)[:80]
    filename = f"{safe_name or 'chat'}.md"
    return Response(
        content=markdown.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{chat_id}/messages", response_model=list[MessageRecord])
async def list_messages(
    request: Request,
    chat_id: str,
    q: str | None = Query(default=None),
) -> list[MessageRecord]:
    state = request.app.state.app_state
    chat = await state.chat_repo.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await state.chat_repo.list_messages(chat_id, q=q)


@router.post("/{chat_id}/messages", response_model=SendMessageResponse)
async def send_message(
    request: Request,
    chat_id: str,
    body: SendMessageRequest,
) -> SendMessageResponse:
    state = request.app.state.app_state
    if not state.settings.api_key:
        raise HTTPException(status_code=401, detail="API key is not configured")

    chat = await state.chat_repo.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    model = get_chat_model(chat.model_id)
    if model and not model.supports_vision:
        for block in body.content:
            if block.type == "image_url":
                raise HTTPException(
                    status_code=400,
                    detail="This model does not support image input",
                )

    try:
        estimate = (model.estimate_credits if model else None) or 0
        await check_can_spend(state.chat_repo, state.app_settings, estimate)
    except SessionLimitExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    message = await state.chat_repo.add_message(chat_id, "user", body.content)
    return SendMessageResponse(message_id=message.id)


@router.get("/{chat_id}/stream")
async def stream_reply(
    request: Request,
    chat_id: str,
    message_id: str = Query(...),
    tools_enabled: bool = Query(default=False),
) -> StreamingResponse:
    state = request.app.state.app_state
    if not state.settings.api_key:
        raise HTTPException(status_code=401, detail="API key is not configured")

    chat = await state.chat_repo.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    trigger = await state.chat_repo.get_message(message_id)
    if not trigger or trigger.chat_id != chat_id or trigger.role != "user":
        raise HTTPException(status_code=400, detail="Invalid trigger message")

    chat_model = get_chat_model(chat.model_id)
    try:
        estimate = (chat_model.estimate_credits if chat_model else None) or 0
        await check_can_spend(state.chat_repo, state.app_settings, estimate)
    except SessionLimitExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    history = await state.chat_repo.list_messages(chat_id)

    async def event_generator() -> AsyncIterator[str]:
        streamer = ChatStreamer(state.kie.http_client)
        full_text = ""
        tokens_in = 0
        tokens_out = 0
        credits = 0.0

        try:
            async for event in streamer.stream_chat(
                chat.model_id,
                history,
                tools_enabled=tools_enabled,
            ):
                if isinstance(event, StreamDelta):
                    full_text += event.text
                    yield _sse_event("delta", {"text": event.text})
                elif isinstance(event, StreamDone):
                    full_text = event.text or full_text
                    tokens_in = event.tokens_in
                    tokens_out = event.tokens_out
                    credits = event.credits
                elif isinstance(event, StreamError):
                    yield _sse_event("error", {"code": event.code, "message": event.message})
                    return

            if full_text:
                assistant_content = [ContentBlock(type="text", text=full_text)]
                await state.chat_repo.add_message(
                    chat_id,
                    "assistant",
                    assistant_content,
                    tokens_in=tokens_in or None,
                    tokens_out=tokens_out or None,
                    credits=credits or None,
                )
                if credits > 0:
                    await record_spent(
                        state.chat_repo,
                        credits,
                        event_bus=state.event_bus,
                        settings=state.app_settings,
                    )
                    await state.event_bus.broadcast(
                        "credits.updated",
                        {"credits_consumed": credits},
                    )

            yield _sse_event(
                "done",
                {
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "credits": credits,
                },
            )
        except KieAuthError as exc:
            yield _sse_event("error", {"code": 401, "message": exc.message})
        except KieInsufficientCreditsError as exc:
            yield _sse_event("error", {"code": 402, "message": exc.message})
        except KieApiError as exc:
            yield _sse_event("error", {"code": exc.code, "message": exc.message})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_chat_file(
    request: Request,
    file: UploadFile = File(...),
) -> UploadResponse:
    state = request.app.state.app_state
    if not state.settings.api_key:
        raise HTTPException(status_code=401, detail="API key is not configured")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    uploader = state.file_uploader
    try:
        url = await uploader.upload_file(file.filename or "upload.jpg", content, content_type)
    except KieAuthError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc
    except KieApiError as exc:
        raise HTTPException(status_code=exc.code, detail=exc.message) from exc

    return UploadResponse(file_url=url)
