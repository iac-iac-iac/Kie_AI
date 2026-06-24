from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture()
def temp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "KieAI"
    data_dir.mkdir()
    monkeypatch.setenv("KIE_DATA_DIR", str(data_dir))
    monkeypatch.delenv("KIE_API_KEY", raising=False)
    return data_dir


@pytest.fixture()
def client(temp_data_dir: Path):
    from starlette.testclient import TestClient

    from kie_sidecar.models.registry import clear_registry_cache
    from kie_sidecar.main import app

    clear_registry_cache()
    with TestClient(app) as test_client:
        yield test_client
