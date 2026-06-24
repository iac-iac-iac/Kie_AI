#!/usr/bin/env python3
"""Dump all market doc paths from llms.txt for analysis."""
import re
import urllib.request
from collections import Counter

text = urllib.request.urlopen("https://docs.kie.ai/llms.txt", timeout=60).read().decode("utf-8")
start = text.find("## API Docs")
section = text[start:]

def norm(line):
    return re.sub(r"\s+", " ", line)

def cat(line):
    n = norm(line)
    if "Image Models" in n: return "image"
    if "Video Models" in n: return "video"
    if "Chat Models" in n: return "chat"
    if "Music Models" in n or "ElevenLabs" in n: return "audio"
    if "Suno API" in n: return "suno"
    if "Veo" in n: return "veo"
    if "4o Image" in n: return "image4o"
    if "Flux Kontext" in n: return "flux_kontext"
    if "Runway" in n: return "runway"
    return "other"

paths = []
for line in section.splitlines():
    if not line.startswith("-") or "/cn/" in line:
        continue
    m = re.search(r"docs\.kie\.ai/([^)]+)", line)
    if not m:
        continue
    p = m.group(1)
    if "callback" in p.lower() or "quickstart" in p.lower():
        continue
    paths.append((cat(line), p))

print("total lines", len(paths))
print("by cat", dict(Counter(c for c,_ in paths)))
print("unique paths", len(set(p for _,p in paths)))
market = [(c,p) for c,p in paths if p.startswith("market/")]
print("market unique", len(set(p for _,p in market)))
for c in ("chat","image","video","audio","suno"):
    items = sorted(set(p for cc,p in market if cc==c))
    print(f"\n=== {c} ({len(items)}) ===")
    for p in items:
        print(p)
