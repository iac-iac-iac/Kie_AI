from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KIE_", extra="ignore")

    api_key: str | None = None
    data_dir: Path = Path(os.environ.get("APPDATA", Path.home())) / "KieAI"
    kie_base_url: str = "https://api.kie.ai"
    host: str = "127.0.0.1"
    port: int = 18765

    @property
    def db_path(self) -> Path:
        return self.data_dir / "data" / "kie.db"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.media_dir / "images").mkdir(parents=True, exist_ok=True)
        (self.media_dir / "videos").mkdir(parents=True, exist_ok=True)
        (self.media_dir / "audio").mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
