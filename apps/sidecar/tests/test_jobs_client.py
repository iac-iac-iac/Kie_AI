from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from kie_sidecar.kie.jobs import JobsClient, _parse_task_record


@pytest.mark.asyncio
async def test_create_task_parses_task_id():
    client = MagicMock()
    response = httpx.Response(
        200,
        json={"code": 200, "data": {"taskId": "abc-123"}},
        request=httpx.Request("POST", "https://api.kie.ai/api/v1/jobs/createTask"),
    )
    client.post = AsyncMock(return_value=response)
    jobs = JobsClient(client)
    task_id = await jobs.create_task("flux-2/flex-text-to-image", {"prompt": "test"})
    assert task_id == "abc-123"
    client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_task_record_success():
    client = MagicMock()
    response = httpx.Response(
        200,
        json={
            "code": 200,
            "data": {
                "state": "success",
                "resultJson": '{"resultUrls": ["https://cdn.example.com/img.png"]}',
                "consumeCredits": 15,
            },
        },
        request=httpx.Request("GET", "https://api.kie.ai/api/v1/jobs/recordInfo"),
    )
    client.get = AsyncMock(return_value=response)
    jobs = JobsClient(client)
    record = await jobs.get_task_record("task-1")
    assert record.state == "success"
    assert record.result_urls == ["https://cdn.example.com/img.png"]
    assert record.credits_consumed == 15.0


@pytest.mark.asyncio
async def test_get_download_url_dict_data():
    client = MagicMock()
    response = httpx.Response(
        200,
        json={"code": 200, "data": {"downloadUrl": "https://signed.example.com/file.png"}},
        request=httpx.Request("POST", "https://api.kie.ai/api/v1/common/download-url"),
    )
    client.post = AsyncMock(return_value=response)
    jobs = JobsClient(client)
    url = await jobs.get_download_url("https://cdn.example.com/img.png")
    assert url == "https://signed.example.com/file.png"


@pytest.mark.asyncio
async def test_get_download_url_string_data():
    client = MagicMock()
    response = httpx.Response(
        200,
        json={"code": 200, "data": "https://signed.example.com/file.png"},
        request=httpx.Request("POST", "https://api.kie.ai/api/v1/common/download-url"),
    )
    client.post = AsyncMock(return_value=response)
    jobs = JobsClient(client)
    url = await jobs.get_download_url("https://cdn.example.com/img.png")
    assert url == "https://signed.example.com/file.png"


@pytest.mark.asyncio
async def test_create_task_string_task_id():
    client = MagicMock()
    response = httpx.Response(
        200,
        json={"code": 200, "data": "task-abc-123"},
        request=httpx.Request("POST", "https://api.kie.ai/api/v1/jobs/createTask"),
    )
    client.post = AsyncMock(return_value=response)
    jobs = JobsClient(client)
    task_id = await jobs.create_task("google/nano-banana", {"prompt": "test"})
    assert task_id == "task-abc-123"


def test_parse_task_record_running():
    record = _parse_task_record("t1", {"state": "generating"})
    assert record.state == "running"


def test_parse_task_record_failed():
    record = _parse_task_record("t1", {"state": "fail", "failMsg": "NSFW"})
    assert record.state == "failed"
    assert record.fail_msg == "NSFW"
