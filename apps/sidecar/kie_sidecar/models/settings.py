from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProxySettings(BaseModel):
    enabled: bool = False
    url: str | None = None


class AppSettings(BaseModel):
    theme: Literal["dark", "light", "system"] = "dark"
    locale: Literal["ru", "en"] = "ru"
    notifications_enabled: bool = True
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    session_limit_enabled: bool = False
    session_limit_credits: float | None = None


class AppSettingsPatch(BaseModel):
    theme: Literal["dark", "light", "system"] | None = None
    locale: Literal["ru", "en"] | None = None
    notifications_enabled: bool | None = None
    proxy: ProxySettings | None = None
    session_limit_enabled: bool | None = None
    session_limit_credits: float | None = None
