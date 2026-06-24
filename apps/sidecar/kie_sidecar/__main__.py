from __future__ import annotations

import os

import uvicorn

from kie_sidecar.main import app


def main() -> None:
    host = os.environ.get("KIE_HOST", "127.0.0.1")
    port = int(os.environ.get("KIE_PORT", os.environ.get("PORT", "18765")))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
