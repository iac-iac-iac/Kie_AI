from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Literal

import httpx

from kie_sidecar.kie.errors import map_kie_error
from kie_sidecar.models.chat import ContentBlock, MessageRecord
from kie_sidecar.models.registry import ChatModelDefinition, get_chat_model


@dataclass
class StreamDelta:
    kind: Literal["delta"] = "delta"
    text: str = ""


@dataclass
class StreamDone:
    kind: Literal["done"] = "done"
    text: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    credits: float = 0.0


@dataclass
class StreamError:
    kind: Literal["error"] = "error"
    code: int = 500
    message: str = ""


StreamEvent = StreamDelta | StreamDone | StreamError


def _blocks_to_claude_content(blocks: list[ContentBlock]) -> list[dict[str, Any]] | str:
    if len(blocks) == 1 and blocks[0].type == "text" and blocks[0].text:
        return blocks[0].text
    result: list[dict[str, Any]] = []
    for block in blocks:
        if block.type == "text" and block.text:
            result.append({"type": "text", "text": block.text})
        elif block.type == "image_url" and block.url:
            result.append({"type": "image", "source": {"type": "url", "url": block.url}})
        elif block.type == "tool_use" and block.tool_use_id:
            result.append(
                {
                    "type": "tool_use",
                    "id": block.tool_use_id,
                    "name": block.name,
                    "input": block.input or {},
                }
            )
        elif block.type == "tool_result" and block.tool_use_id:
            result.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.tool_use_id,
                    "content": block.content or "",
                }
            )
    return result if result else ""


def _blocks_to_openai_content(blocks: list[ContentBlock]) -> str | list[dict[str, Any]]:
    if len(blocks) == 1 and blocks[0].type == "text" and blocks[0].text:
        return blocks[0].text
    result: list[dict[str, Any]] = []
    for block in blocks:
        if block.type == "text" and block.text:
            result.append({"type": "text", "text": block.text})
        elif block.type == "image_url" and block.url:
            result.append({"type": "image_url", "image_url": {"url": block.url}})
    return result if result else ""


def _messages_to_api(
    model: ChatModelDefinition,
    messages: list[MessageRecord],
) -> list[dict[str, Any]]:
    api_messages: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == "tool":
            continue
        if model.api_style == "claude":
            api_messages.append(
                {"role": msg.role, "content": _blocks_to_claude_content(msg.content)}
            )
        else:
            api_messages.append(
                {"role": msg.role, "content": _blocks_to_openai_content(msg.content)}
            )
    return api_messages


class ChatStreamer:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def stream_chat(
        self,
        model_id: str,
        messages: list[MessageRecord],
        *,
        tools_enabled: bool = False,
    ) -> AsyncIterator[StreamEvent]:
        model = get_chat_model(model_id)
        if not model:
            yield StreamError(code=400, message=f"Unknown model: {model_id}")
            return

        body: dict[str, Any] = {
            "model": model.model_field,
            "stream": True,
            "messages": _messages_to_api(model, messages),
            **model.default_params,
        }
        if tools_enabled and model.supports_tools and model.api_style == "claude":
            body["tools"] = [
                {
                    "name": "get_current_time",
                    "description": "Returns the current UTC time as ISO string",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                }
            ]

        try:
            async with self._client.stream(
                "POST",
                model.api_path,
                json=body,
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code >= 400:
                    raw = await response.aread()
                    try:
                        err_body = json.loads(raw)
                        code = int(err_body.get("code", response.status_code))
                        msg = str(err_body.get("msg", raw.decode()))
                    except (json.JSONDecodeError, ValueError):
                        code = response.status_code
                        msg = raw.decode(errors="replace")
                    kie_err = map_kie_error(code, msg)
                    yield StreamError(code=kie_err.code, message=kie_err.message)
                    return

                if model.api_style == "claude":
                    async for event in self._parse_claude_stream(response):
                        yield event
                else:
                    async for event in self._parse_openai_stream(response):
                        yield event
        except httpx.HTTPError as exc:
            yield StreamError(code=503, message=f"Network error: {exc}")

    async def _parse_claude_stream(
        self, response: httpx.Response
    ) -> AsyncIterator[StreamEvent]:
        full_text: list[str] = []
        tokens_in = 0
        tokens_out = 0
        credits = 0.0
        event_name = ""

        async for line in response.aiter_lines():
            if line.startswith("event:"):
                event_name = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if event_name == "content_block_delta":
                delta = data.get("delta", {})
                text = delta.get("text", "")
                if text:
                    full_text.append(text)
                    yield StreamDelta(text=text)
            elif event_name == "message_delta":
                usage = data.get("usage", {})
                tokens_out = int(usage.get("output_tokens", tokens_out))
            elif event_name == "message_start":
                message = data.get("message", {})
                usage = message.get("usage", {})
                tokens_in = int(usage.get("input_tokens", tokens_in))
            elif data.get("type") == "message_delta":
                usage = data.get("usage", {})
                tokens_out = int(usage.get("output_tokens", tokens_out))

            credits = float(
                data.get("credits_consumed")
                or data.get("message", {}).get("credits_consumed")
                or credits
            )
            usage = data.get("usage") or data.get("message", {}).get("usage", {})
            if usage:
                tokens_in = int(usage.get("input_tokens", tokens_in))
                tokens_out = int(usage.get("output_tokens", tokens_out))

        yield StreamDone(
            text="".join(full_text),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            credits=credits,
        )

    async def _parse_openai_stream(
        self, response: httpx.Response
    ) -> AsyncIterator[StreamEvent]:
        full_text: list[str] = []
        tokens_in = 0
        tokens_out = 0
        credits = 0.0

        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            choices = data.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                text = delta.get("content", "")
                if text:
                    full_text.append(text)
                    yield StreamDelta(text=text)

            usage = data.get("usage")
            if usage:
                tokens_in = int(usage.get("prompt_tokens", tokens_in))
                tokens_out = int(usage.get("completion_tokens", tokens_out))
            if data.get("credits_consumed") is not None:
                credits = float(data["credits_consumed"])

        yield StreamDone(
            text="".join(full_text),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            credits=credits,
        )
