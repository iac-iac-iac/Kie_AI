from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from kie_sidecar.kie.errors import KieApiError, map_kie_error
from kie_sidecar.kie.jobs import TaskRecord, TaskState

SUNO_CALLBACK_URL = "https://localhost/kie-ai/noop"

RecordKind = Literal["music", "lyrics", "vocal_removal", "wav", "mp4", "midi", "sync"]

SUNO_OPERATIONS: dict[str, dict[str, str]] = {
    "generate": {"create": "/api/v1/generate", "record": "music"},
    "lyrics": {"create": "/api/v1/lyrics", "record": "lyrics"},
    "extend": {"create": "/api/v1/generate/extend", "record": "music"},
    "upload_cover": {"create": "/api/v1/generate/upload-cover", "record": "music"},
    "upload_extend": {"create": "/api/v1/generate/upload-extend", "record": "music"},
    "add_instrumental": {"create": "/api/v1/generate/add-instrumental", "record": "music"},
    "add_vocals": {"create": "/api/v1/generate/add-vocals", "record": "music"},
    "separate_vocals": {"create": "/api/v1/vocal-removal/generate", "record": "vocal_removal"},
    "convert_wav": {"create": "/api/v1/wav/generate", "record": "wav"},
    "music_video": {"create": "/api/v1/mp4/generate", "record": "mp4"},
    "boost_style": {"create": "/api/v1/style/generate", "record": "style"},
    "persona": {"create": "/api/v1/generate/generate-persona", "record": "sync"},
    "midi": {"create": "/api/v1/midi/generate", "record": "midi"},
    "generate_sounds": {"create": "/api/v1/generate/generate-sounds", "record": "music"},
}

RECORD_PATHS: dict[str, str] = {
    "music": "/api/v1/generate/record-info",
    "lyrics": "/api/v1/lyrics/record-info",
    "vocal_removal": "/api/v1/vocal-removal/record-info",
    "wav": "/api/v1/wav/record-info",
    "mp4": "/api/v1/mp4/record-info",
    "midi": "/api/v1/midi/record-info",
    "style": "/api/v1/style/record-info",
}

_MUSIC_FAILED = frozenset(
    {
        "CREATE_TASK_FAILED",
        "GENERATE_AUDIO_FAILED",
        "CALLBACK_EXCEPTION",
        "SENSITIVE_WORD_ERROR",
    }
)
_LYRICS_FAILED = frozenset(
    {
        "CREATE_TASK_FAILED",
        "GENERATE_LYRICS_FAILED",
        "CALLBACK_EXCEPTION",
        "SENSITIVE_WORD_ERROR",
    }
)

_FIELD_MAP = {
    "custom_mode": "customMode",
    "negative_tags": "negativeTags",
    "upload_url": "uploadUrl",
    "audio_id": "audioId",
    "task_id": "taskId",
    "default_param_flag": "defaultParamFlag",
    "continue_at": "continueAt",
    "vocal_gender": "vocalGender",
    "style_weight": "styleWeight",
    "weirdness_constraint": "weirdnessConstraint",
    "audio_weight": "audioWeight",
    "persona_id": "personaId",
    "persona_model": "personaModel",
    "vocal_start": "vocalStart",
    "vocal_end": "vocalEnd",
}


@dataclass
class SunoTaskRecord:
    task_id: str
    state: TaskState
    result_urls: list[str]
    text_content: str | None
    credits_consumed: float | None
    fail_msg: str | None
    raw: dict[str, Any]


@dataclass
class SunoCreateResult:
    task_id: str | None
    sync_data: dict[str, Any] | None


class SunoClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def _parse_response(self, response: httpx.Response) -> Any:
        try:
            body = response.json()
        except ValueError:
            body = {"msg": response.text}

        if response.status_code >= 400:
            code = body.get("code", response.status_code) if isinstance(body, dict) else response.status_code
            msg = body.get("msg", response.text) if isinstance(body, dict) else response.text
            raise map_kie_error(int(code), str(msg))

        if isinstance(body, dict) and body.get("code") not in (None, 200):
            raise map_kie_error(int(body.get("code", 500)), str(body.get("msg", "Unknown error")))

        return body

    @staticmethod
    def _unwrap_data(body: Any) -> Any:
        if not isinstance(body, dict):
            return {}
        return body.get("data")

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}

    async def create_task(self, operation: str, payload: dict[str, Any]) -> SunoCreateResult:
        op = SUNO_OPERATIONS.get(operation)
        if not op:
            raise ValueError(f"Unknown Suno operation: {operation}")
        response = await self._client.post(op["create"], json=payload)
        body = await self._parse_response(response)
        data = self._as_dict(self._unwrap_data(body))
        if op["record"] == "sync":
            return SunoCreateResult(task_id=None, sync_data=data)
        task_id = data.get("taskId") or data.get("task_id")
        if not task_id:
            raise KieApiError(500, f"Missing taskId in Suno {operation} response")
        return SunoCreateResult(task_id=str(task_id), sync_data=None)

    async def get_record(self, operation: str, task_id: str) -> SunoTaskRecord:
        op = SUNO_OPERATIONS.get(operation)
        if not op:
            raise ValueError(f"Unknown Suno operation: {operation}")
        record_kind = op["record"]
        if record_kind == "sync":
            raise ValueError("Sync operations do not support polling")
        path = RECORD_PATHS.get(record_kind)
        if not path:
            raise ValueError(f"No record path for {record_kind}")
        response = await self._client.get(path, params={"taskId": task_id})
        body = await self._parse_response(response)
        data = self._as_dict(self._unwrap_data(body))
        if record_kind == "lyrics":
            return _parse_lyrics_record(task_id, data)
        if record_kind == "vocal_removal":
            return _parse_vocal_removal_record(task_id, data)
        if record_kind == "style":
            return _parse_style_record(task_id, data)
        return _parse_music_record(task_id, data)

    async def create_generate(self, payload: dict[str, Any]) -> str:
        result = await self.create_task("generate", payload)
        assert result.task_id
        return result.task_id

    async def get_music_record(self, task_id: str) -> SunoTaskRecord:
        return await self.get_record("generate", task_id)


def build_suno_payload(
    operation: str,
    model_field: str,
    validated_input: dict[str, Any],
    parameters: list[Any] | None = None,
) -> dict[str, Any]:
    if operation == "generate":
        return _build_generate_payload(model_field, validated_input)
    if operation == "lyrics":
        prompt = str(validated_input.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("Missing required parameter: prompt")
        return {"prompt": prompt, "callBackUrl": SUNO_CALLBACK_URL}
    if operation == "persona":
        return _build_persona_payload(validated_input)
    if operation == "extend":
        return _build_extend_payload(model_field, validated_input)
    if operation in ("upload_cover", "upload_extend"):
        return _build_upload_music_payload(model_field, validated_input)
    if operation == "add_instrumental":
        return _build_add_instrumental_payload(model_field, validated_input)
    if operation == "add_vocals":
        return _build_add_vocals_payload(model_field, validated_input)
    if operation == "separate_vocals":
        return _build_separate_vocals_payload(validated_input)
    if operation == "convert_wav":
        return _build_convert_wav_payload(validated_input)
    if operation == "music_video":
        return _build_music_video_payload(validated_input)
    if operation == "boost_style":
        return _build_boost_style_payload(validated_input)
    if operation == "midi":
        return _build_midi_payload(validated_input)
    if operation == "generate_sounds":
        return _build_generate_sounds_payload(validated_input)
    raise ValueError(f"Unsupported Suno operation: {operation}")


def _build_generate_payload(model_field: str, validated_input: dict[str, Any]) -> dict[str, Any]:
    custom_mode = bool(validated_input.get("custom_mode", False))
    prompt = str(validated_input.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("Missing required parameter: prompt")

    payload: dict[str, Any] = {
        "prompt": prompt,
        "customMode": custom_mode,
        "instrumental": bool(validated_input.get("instrumental", False)),
        "model": model_field,
        "callBackUrl": SUNO_CALLBACK_URL,
    }

    if custom_mode:
        style = str(validated_input.get("style", "")).strip()
        title = str(validated_input.get("title", "")).strip()
        if not style:
            raise ValueError("style is required when custom_mode is enabled")
        if not title:
            raise ValueError("title is required when custom_mode is enabled")
        payload["style"] = style
        payload["title"] = title

    negative_tags = str(validated_input.get("negative_tags", "")).strip()
    if negative_tags:
        payload["negativeTags"] = negative_tags

    return payload


def _build_extend_payload(model_field: str, validated_input: dict[str, Any]) -> dict[str, Any]:
    audio_id = str(validated_input.get("audio_id", "")).strip()
    if not audio_id:
        raise ValueError("Missing required parameter: audio_id")

    default_param_flag = bool(validated_input.get("default_param_flag", True))
    payload: dict[str, Any] = {
        "audioId": audio_id,
        "defaultParamFlag": default_param_flag,
        "model": model_field,
        "callBackUrl": SUNO_CALLBACK_URL,
        "prompt": str(validated_input.get("prompt", "")).strip(),
    }

    if default_param_flag:
        style = str(validated_input.get("style", "")).strip()
        title = str(validated_input.get("title", "")).strip()
        continue_at = validated_input.get("continue_at")
        if not style:
            raise ValueError("style is required when default_param_flag is enabled")
        if not title:
            raise ValueError("title is required when default_param_flag is enabled")
        if continue_at is None or continue_at == "":
            raise ValueError("continue_at is required when default_param_flag is enabled")
        payload["style"] = style
        payload["title"] = title
        payload["continueAt"] = float(continue_at)

    _apply_optional(payload, validated_input, ("negative_tags", "negativeTags"), ("vocal_gender", "vocalGender"))
    return payload


def _build_upload_music_payload(model_field: str, validated_input: dict[str, Any]) -> dict[str, Any]:
    upload_url = str(validated_input.get("upload_url", "")).strip()
    prompt = str(validated_input.get("prompt", "")).strip()
    if not upload_url:
        raise ValueError("Missing required parameter: upload_url")
    if not prompt:
        raise ValueError("Missing required parameter: prompt")

    custom_mode = bool(validated_input.get("custom_mode", False))
    payload: dict[str, Any] = {
        "uploadUrl": upload_url,
        "prompt": prompt,
        "customMode": custom_mode,
        "instrumental": bool(validated_input.get("instrumental", False)),
        "model": model_field,
        "callBackUrl": SUNO_CALLBACK_URL,
    }
    if custom_mode:
        style = str(validated_input.get("style", "")).strip()
        title = str(validated_input.get("title", "")).strip()
        if not style:
            raise ValueError("style is required when custom_mode is enabled")
        if not title:
            raise ValueError("title is required when custom_mode is enabled")
        payload["style"] = style
        payload["title"] = title
    negative_tags = str(validated_input.get("negative_tags", "")).strip()
    if negative_tags:
        payload["negativeTags"] = negative_tags
    return payload


def _build_add_instrumental_payload(model_field: str, validated_input: dict[str, Any]) -> dict[str, Any]:
    upload_url = str(validated_input.get("upload_url", "")).strip()
    title = str(validated_input.get("title", "")).strip()
    tags = str(validated_input.get("tags", "")).strip()
    negative_tags = str(validated_input.get("negative_tags", "")).strip()
    if not upload_url or not title or not tags or not negative_tags:
        raise ValueError("upload_url, title, tags, and negative_tags are required")
    return {
        "uploadUrl": upload_url,
        "model": model_field,
        "title": title,
        "tags": tags,
        "negativeTags": negative_tags,
        "callBackUrl": SUNO_CALLBACK_URL,
    }


def _build_add_vocals_payload(model_field: str, validated_input: dict[str, Any]) -> dict[str, Any]:
    upload_url = str(validated_input.get("upload_url", "")).strip()
    prompt = str(validated_input.get("prompt", "")).strip()
    title = str(validated_input.get("title", "")).strip()
    style = str(validated_input.get("style", "")).strip()
    if not upload_url or not prompt or not title or not style:
        raise ValueError("upload_url, prompt, title, and style are required")
    return {
        "uploadUrl": upload_url,
        "model": model_field,
        "prompt": prompt,
        "title": title,
        "style": style,
        "callBackUrl": SUNO_CALLBACK_URL,
    }


def _build_separate_vocals_payload(validated_input: dict[str, Any]) -> dict[str, Any]:
    task_id = str(validated_input.get("task_id", "")).strip()
    audio_id = str(validated_input.get("audio_id", "")).strip()
    if not task_id or not audio_id:
        raise ValueError("task_id and audio_id are required")
    payload: dict[str, Any] = {
        "taskId": task_id,
        "audioId": audio_id,
        "callBackUrl": SUNO_CALLBACK_URL,
    }
    sep_type = str(validated_input.get("type", "separate_vocal")).strip()
    if sep_type:
        payload["type"] = sep_type
    return payload


def _build_convert_wav_payload(validated_input: dict[str, Any]) -> dict[str, Any]:
    task_id = str(validated_input.get("task_id", "")).strip()
    audio_id = str(validated_input.get("audio_id", "")).strip()
    if not task_id or not audio_id:
        raise ValueError("task_id and audio_id are required")
    return {
        "taskId": task_id,
        "audioId": audio_id,
        "callBackUrl": SUNO_CALLBACK_URL,
    }


def _build_music_video_payload(validated_input: dict[str, Any]) -> dict[str, Any]:
    task_id = str(validated_input.get("task_id", "")).strip()
    audio_id = str(validated_input.get("audio_id", "")).strip()
    if not task_id or not audio_id:
        raise ValueError("task_id and audio_id are required")
    return {
        "taskId": task_id,
        "audioId": audio_id,
        "callBackUrl": SUNO_CALLBACK_URL,
    }


def _build_boost_style_payload(validated_input: dict[str, Any]) -> dict[str, Any]:
    content = str(validated_input.get("content", "")).strip()
    if not content:
        raise ValueError("Missing required parameter: content")
    return {"content": content, "callBackUrl": SUNO_CALLBACK_URL}


def _build_midi_payload(validated_input: dict[str, Any]) -> dict[str, Any]:
    task_id = str(validated_input.get("task_id", "")).strip()
    audio_id = str(validated_input.get("audio_id", "")).strip()
    if not task_id or not audio_id:
        raise ValueError("task_id and audio_id are required")
    return {
        "taskId": task_id,
        "audioId": audio_id,
        "callBackUrl": SUNO_CALLBACK_URL,
    }


def _build_generate_sounds_payload(validated_input: dict[str, Any]) -> dict[str, Any]:
    prompt = str(validated_input.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("Missing required parameter: prompt")
    return {"prompt": prompt, "callBackUrl": SUNO_CALLBACK_URL}


def _build_persona_payload(validated_input: dict[str, Any]) -> dict[str, Any]:
    task_id = str(validated_input.get("task_id", "")).strip()
    audio_id = str(validated_input.get("audio_id", "")).strip()
    name = str(validated_input.get("name", "")).strip()
    description = str(validated_input.get("description", "")).strip()
    if not task_id or not audio_id or not name or not description:
        raise ValueError("task_id, audio_id, name, and description are required")
    payload: dict[str, Any] = {
        "taskId": task_id,
        "audioId": audio_id,
        "name": name,
        "description": description,
    }
    style = str(validated_input.get("style", "")).strip()
    if style:
        payload["style"] = style
    if validated_input.get("vocal_start") is not None:
        payload["vocalStart"] = float(validated_input["vocal_start"])
    if validated_input.get("vocal_end") is not None:
        payload["vocalEnd"] = float(validated_input["vocal_end"])
    return payload


def _apply_optional(
    payload: dict[str, Any],
    validated_input: dict[str, Any],
    *pairs: tuple[str, str],
) -> None:
    for src, dst in pairs:
        value = validated_input.get(src)
        if value is None or value == "":
            continue
        payload[dst] = value


def suno_to_task_record(record: SunoTaskRecord) -> TaskRecord:
    return TaskRecord(
        task_id=record.task_id,
        state=record.state,
        result_urls=record.result_urls,
        credits_consumed=record.credits_consumed,
        fail_msg=record.fail_msg,
        raw=record.raw,
    )


def _parse_music_record(task_id: str, data: dict[str, Any]) -> SunoTaskRecord:
    raw_status = str(data.get("status") or "PENDING").upper()
    state = _map_music_status(raw_status)
    result_urls = _extract_audio_urls(data)
    fail_msg = data.get("errorMessage") or data.get("error_message")
    if raw_status in _MUSIC_FAILED and not fail_msg:
        fail_msg = raw_status.replace("_", " ").title()
    return SunoTaskRecord(
        task_id=task_id,
        state=state,
        result_urls=result_urls,
        text_content=None,
        credits_consumed=None,
        fail_msg=str(fail_msg) if fail_msg else None,
        raw=data,
    )


def _parse_lyrics_record(task_id: str, data: dict[str, Any]) -> SunoTaskRecord:
    raw_status = str(data.get("status") or "PENDING").upper()
    if raw_status == "SUCCESS":
        state: TaskState = "success"
    elif raw_status in _LYRICS_FAILED:
        state = "failed"
    else:
        state = "pending"

    text_content = _extract_lyrics_text(data)
    fail_msg = data.get("errorMessage") or data.get("error_message")
    if raw_status in _LYRICS_FAILED and not fail_msg:
        fail_msg = raw_status.replace("_", " ").title()
    return SunoTaskRecord(
        task_id=task_id,
        state=state,
        result_urls=[],
        text_content=text_content,
        credits_consumed=None,
        fail_msg=str(fail_msg) if fail_msg else None,
        raw=data,
    )


def _parse_style_record(task_id: str, data: dict[str, Any]) -> SunoTaskRecord:
    raw_status = str(data.get("status") or "PENDING").upper()
    if raw_status == "SUCCESS":
        state: TaskState = "success"
    elif raw_status in _MUSIC_FAILED:
        state = "failed"
    else:
        state = "pending"

    text_content = _extract_style_text(data)
    fail_msg = data.get("errorMessage") or data.get("error_message")
    return SunoTaskRecord(
        task_id=task_id,
        state=state,
        result_urls=[],
        text_content=text_content,
        credits_consumed=None,
        fail_msg=str(fail_msg) if fail_msg else None,
        raw=data,
    )


def _parse_vocal_removal_record(task_id: str, data: dict[str, Any]) -> SunoTaskRecord:
    raw_status = str(data.get("status") or "PENDING").upper()
    if raw_status == "SUCCESS":
        state: TaskState = "success"
    elif raw_status in _MUSIC_FAILED:
        state = "failed"
    else:
        state = "pending"

    urls = _extract_vocal_removal_urls(data)
    fail_msg = data.get("errorMessage") or data.get("error_message")
    return SunoTaskRecord(
        task_id=task_id,
        state=state,
        result_urls=urls,
        text_content=None,
        credits_consumed=None,
        fail_msg=str(fail_msg) if fail_msg else None,
        raw=data,
    )


def _map_music_status(raw_status: str) -> TaskState:
    if raw_status == "SUCCESS":
        return "success"
    if raw_status in _MUSIC_FAILED:
        return "failed"
    if raw_status in ("TEXT_SUCCESS", "FIRST_SUCCESS"):
        return "running"
    return "pending"


def _extract_audio_urls(data: dict[str, Any]) -> list[str]:
    response = data.get("response")
    if not isinstance(response, dict):
        return []
    suno_data = response.get("sunoData") or response.get("suno_data")
    if not isinstance(suno_data, list):
        return []
    urls: list[str] = []
    for item in suno_data:
        if not isinstance(item, dict):
            continue
        for key in ("audioUrl", "audio_url", "streamAudioUrl", "stream_audio_url"):
            url = item.get(key)
            if isinstance(url, str) and url.strip():
                urls.append(url.strip())
                break
    return list(dict.fromkeys(urls))


def _extract_style_text(data: dict[str, Any]) -> str | None:
    response = data.get("response")
    if isinstance(response, dict):
        for key in ("content", "style", "text", "result"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("content", "style", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_lyrics_text(data: dict[str, Any]) -> str | None:
    response = data.get("response")
    if not isinstance(response, dict):
        return None
    items = response.get("data")
    if not isinstance(items, list) or not items:
        return None
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        text = str(item.get("text") or "").strip()
        if title and text:
            parts.append(f"# {title}\n\n{text}")
        elif text:
            parts.append(text)
    return "\n\n---\n\n".join(parts) if parts else None


def _extract_vocal_removal_urls(data: dict[str, Any]) -> list[str]:
    response = data.get("response")
    if not isinstance(response, dict):
        info = data.get("vocal_separation_info") or data.get("vocalSeparationInfo")
        if isinstance(info, dict):
            response = info
        else:
            return []
    urls: list[str] = []
    for key, value in response.items():
        if isinstance(value, str) and value.strip().endswith((".mp3", ".wav", ".ogg")):
            urls.append(value.strip())
    return list(dict.fromkeys(urls))
