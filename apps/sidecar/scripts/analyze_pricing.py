#!/usr/bin/env python3
"""Analyze kie.ai model-pricing vs model-paths."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1] / "catalog"
pricing = json.loads((ROOT / "model_pricing_all.json").read_text(encoding="utf-8-sig"))
paths = set(json.loads((ROOT / "model_paths.json").read_text(encoding="utf-8-sig")))

by_iface = Counter(p["interfaceType"] for p in pricing)
print("pricing rows by interfaceType:", dict(by_iface))

# Extract model id from anchor
from_anchor: list[tuple[str, str]] = []
for p in pricing:
    anchor = p.get("anchor") or ""
    m = re.search(r"model=([^&]+)", anchor)
    if m:
        from_anchor.append((p["interfaceType"], unquote(m.group(1))))

print(f"pricing with anchor model param: {len(from_anchor)}, unique: {len(set(x[1] for x in from_anchor))}")

# Description first token patterns
desc_bases = [(p["interfaceType"], p["modelDescription"].split(",")[0].strip()) for p in pricing]
print(f"unique description bases: {len(set(desc_bases))}")
for iface in ("chat", "image", "video", "music"):
    bases = sorted({b for i, b in desc_bases if i == iface})
    print(f"\n=== {iface} unique bases ({len(bases)}) ===")
    for b in bases[:15]:
        print(f"  {b}")
    if len(bases) > 15:
        print(f"  ... +{len(bases)-15} more")

print(f"\nmodel-paths count: {len(paths)}")

# paths not in desc bases
desc_ids = {b for _, b in desc_bases}
missing_paths = sorted(paths - desc_ids)
extra_bases = sorted(desc_ids - paths)
print(f"paths not in desc bases: {len(missing_paths)}")
for p in missing_paths[:20]:
    print(f"  path-only: {p}")
print(f"desc bases not in paths: {len(extra_bases)}")
for b in extra_bases[:20]:
    print(f"  desc-only: {b}")
