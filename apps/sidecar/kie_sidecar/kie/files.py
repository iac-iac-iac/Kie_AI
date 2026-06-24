from __future__ import annotations

import httpx

from kie_sidecar.kie.errors import KieApiError, map_kie_error
from kie_sidecar.models.settings import ProxySettings


UPLOAD_BASE_URL = "https://kieai.redpandaai.co"
UPLOAD_PATH = "images/user-uploads"


class FileUploader:
    def __init__(
        self,
        api_key: str | None,
        proxy: ProxySettings | None = None,
    ) -> None:
        self._api_key = api_key
        self._proxy = proxy or ProxySettings()
        self._client = self._build_client()

    def _build_client(self) -> httpx.AsyncClient:
        proxy_url = self._proxy.url if self._proxy.enabled and self._proxy.url else None
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return httpx.AsyncClient(
            base_url=UPLOAD_BASE_URL,
            timeout=httpx.Timeout(120.0, connect=15.0),
            proxy=proxy_url,
            trust_env=False,
            headers=headers,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def reload_proxy(self, proxy: ProxySettings) -> None:
        await self._client.aclose()
        self._proxy = proxy
        self._client = self._build_client()

    def update_credentials(self, api_key: str | None) -> None:
        self._api_key = api_key
        if api_key:
            self._client.headers["Authorization"] = f"Bearer {api_key}"
        elif "Authorization" in self._client.headers:
            del self._client.headers["Authorization"]

    async def upload_file(
        self,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> str:
        if not self._api_key:
            raise KieApiError(401, "API key is not configured")

        response = await self._client.post(
            "/api/file-stream-upload",
            files={"file": (filename, content, content_type)},
            data={"uploadPath": UPLOAD_PATH, "fileName": filename},
        )
        try:
            body = response.json()
        except ValueError:
            body = {"msg": response.text}

        if response.status_code >= 400:
            code = body.get("code", response.status_code) if isinstance(body, dict) else response.status_code
            msg = body.get("msg", response.text) if isinstance(body, dict) else response.text
            raise map_kie_error(int(code), str(msg))

        if isinstance(body, dict) and body.get("code") not in (None, 200):
            raise map_kie_error(int(body.get("code", 500)), str(body.get("msg", "Upload failed")))

        data = body.get("data", body) if isinstance(body, dict) else body
        if isinstance(data, dict):
            url = (
                data.get("downloadUrl")
                or data.get("fileUrl")
                or data.get("url")
                or data.get("file_url")
            )
            if url:
                return str(url)
        raise KieApiError(500, "Upload response missing file URL")
