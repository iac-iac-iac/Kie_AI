from __future__ import annotations

from typing import Any

import httpx

from kie_sidecar.kie.errors import KieApiError, map_kie_error
from kie_sidecar.models.settings import AppSettings, ProxySettings


class KieClient:
    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        proxy: ProxySettings | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._proxy = proxy or ProxySettings()
        self._client = self._build_client()

    def _build_client(self) -> httpx.AsyncClient:
        proxy_url = self._proxy.url if self._proxy.enabled and self._proxy.url else None
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(60.0, connect=15.0),
            proxy=proxy_url,
            trust_env=False,
            headers=self._auth_headers(),
        )

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def update_credentials(self, api_key: str | None) -> None:
        self._api_key = api_key
        if api_key:
            self._client.headers["Authorization"] = f"Bearer {api_key}"
        elif "Authorization" in self._client.headers:
            del self._client.headers["Authorization"]

    async def reload_proxy(self, proxy: ProxySettings) -> None:
        await self._client.aclose()
        self._proxy = proxy
        self._client = self._build_client()

    async def close(self) -> None:
        await self._client.aclose()

    @property
    def http_client(self) -> httpx.AsyncClient:
        return self._client

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

    async def get_credits(self) -> float:
        if not self._api_key:
            raise KieApiError(401, "API key is not configured")
        response = await self._client.get("/api/v1/chat/credit")
        body = await self._parse_response(response)
        data = body.get("data", 0)
        return float(data)
