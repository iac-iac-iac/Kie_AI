from __future__ import annotations

from pathlib import Path

import httpx

from kie_sidecar.models.settings import ProxySettings


class MediaDownloader:
    def __init__(self, proxy: ProxySettings | None = None) -> None:
        self._proxy = proxy or ProxySettings()
        self._client = self._build_client()

    def _build_client(self) -> httpx.AsyncClient:
        proxy_url = self._proxy.url if self._proxy.enabled and self._proxy.url else None
        return httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=60.0),
            proxy=proxy_url,
            trust_env=False,
            follow_redirects=True,
        )

    async def reload_proxy(self, proxy: ProxySettings) -> None:
        await self._client.aclose()
        self._proxy = proxy
        self._client = self._build_client()

    async def close(self) -> None:
        await self._client.aclose()

    async def download_to_path(self, url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with self._client.stream("GET", url) as response:
            response.raise_for_status()
            with dest.open("wb") as file:
                async for chunk in response.aiter_bytes(65536):
                    file.write(chunk)
