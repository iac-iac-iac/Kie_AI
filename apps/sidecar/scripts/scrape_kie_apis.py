#!/usr/bin/env python3
"""Find playground API paths in kie.ai frontend bundles."""
from __future__ import annotations

import re
import urllib.request

html = urllib.request.urlopen("https://kie.ai/market", timeout=30).read().decode("utf-8", errors="replace")
chunks = re.findall(r"/_next/static/chunks/[^\"']+\.js", html)
print(f"chunks in HTML: {len(chunks)}")

apis: set[str] = set()
for ch in chunks:
    try:
        js = urllib.request.urlopen("https://kie.ai" + ch, timeout=15).read().decode("utf-8", errors="replace")
    except Exception:
        continue
    apis.update(re.findall(r"/api/v1/playground/[a-zA-Z]+", js))
    apis.update(re.findall(r"playground/[A-Za-z]+", js))

for a in sorted(apis):
    print(a)
print(f"total: {len(apis)}")
