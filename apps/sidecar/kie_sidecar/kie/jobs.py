from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from kie_sidecar.kie.errors import KieApiError, map_kie_error

TaskState = Literal["pending", "running", "success", "failed"]


@dataclass
class TaskRecord:
    task_id: str
    state: TaskState
    result_urls: list[str]
    credits_consumed: float | None
    fail_msg: str | None
    raw: dict[str, Any]


class JobsClient:
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
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        return {}

    async def create_task(self, model: str, input_data: dict[str, Any]) -> str:
        response = await self._client.post(
            "/api/v1/jobs/createTask",
            json={"model": model, "input": input_data},
        )
        body = await self._parse_response(response)
        data = self._unwrap_data(body)
        if isinstance(data, str) and data:
            return data
        data_dict = self._as_dict(data)
        task_id = data_dict.get("taskId") or data_dict.get("task_id")
        if not task_id:
            raise KieApiError(500, "Missing taskId in createTask response")
        return str(task_id)

    async def get_task_record(self, task_id: str) -> TaskRecord:
        response = await self._client.get(
            "/api/v1/jobs/recordInfo",
            params={"taskId": task_id},
        )
        body = await self._parse_response(response)
        data = self._as_dict(self._unwrap_data(body))
        return _parse_task_record(task_id, data)

    async def get_download_url(self, remote_url: str) -> str:
        response = await self._client.post(
            "/api/v1/common/download-url",
            json={"url": remote_url},
        )
        body = await self._parse_response(response)
        data = self._unwrap_data(body)
        if isinstance(data, str) and data:
            return data
        data_dict = self._as_dict(data)
        download_url = (
            data_dict.get("downloadUrl")
            or data_dict.get("download_url")
            or data_dict.get("url")
        )
        if not download_url:
            raise KieApiError(500, "Missing download URL in response")
        return str(download_url)

    async def download_bytes(self, url: str) -> bytes:
        timeout = httpx.Timeout(120.0, connect=30.0)
        response = await self._client.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.content


def _parse_task_record(task_id: str, data: dict[str, Any]) -> TaskRecord:
    raw_state = (
        data.get("state")
        or data.get("status")
        or data.get("taskStatus")
        or "pending"
    )
    state = _normalize_state(str(raw_state))
    result_urls = _extract_result_urls(data)
    credits = _extract_credits(data)
    fail_msg = data.get("failMsg") or data.get("fail_msg") or data.get("errorMsg")
    return TaskRecord(
        task_id=task_id,
        state=state,
        result_urls=result_urls,
        credits_consumed=credits,
        fail_msg=str(fail_msg) if fail_msg else None,
        raw=data,
    )


def _normalize_state(raw: str) -> TaskState:
    lowered = raw.lower()
    if lowered in ("success", "succeed", "completed", "done"):
        return "success"
    if lowered in ("fail", "failed", "error"):
        return "failed"
    if lowered in ("running", "processing", "generating"):
        return "running"
    return "pending"


def _extract_credits(data: dict[str, Any]) -> float | None:
    for key in ("consumeCredits", "consume_credits", "credits_consumed", "creditsConsumed"):
        if key in data and data[key] is not None:
            return float(data[key])
    return None


def _extract_result_urls(data: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("resultUrls", "result_urls", "outputUrls", "output_urls"):
        value = data.get(key)
        if isinstance(value, list):
            urls.extend(str(u) for u in value if u)
    result_json = data.get("resultJson") or data.get("result_json")
    if result_json:
        try:
            parsed = json.loads(result_json) if isinstance(result_json, str) else result_json
            if isinstance(parsed, dict):
                for key in ("resultUrls", "result_urls", "url", "image_url", "imageUrl"):
                    value = parsed.get(key)
                    if isinstance(value, str) and value:
                        urls.append(value)
                    elif isinstance(value, list):
                        urls.extend(str(u) for u in value if u)
            elif isinstance(parsed, list):
                urls.extend(str(u) for u in parsed if u)
        except (json.JSONDecodeError, TypeError):
            pass
    for key in ("url", "imageUrl", "image_url", "outputUrl"):
        value = data.get(key)
        if isinstance(value, str) and value:
            urls.append(value)
    return list(dict.fromkeys(urls))
