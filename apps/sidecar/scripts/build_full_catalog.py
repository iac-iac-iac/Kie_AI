#!/usr/bin/env python3
"""DEPRECATED: use build_market_manifest.py (unique models, not pricing SKUs)."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "catalog" / "full_catalog.json"

CHAT_PATH_MAP = {
    "gpt-5-2": "gpt-5-2",
    "gpt-5-4": "gpt-5-4",
    "gpt-5-5": "gpt-5-5",
    "gpt-5-6": "gpt-5-6",
    "claude-haiku-4-5": "claude-haiku-4-5",
    "claude-opus-4-5": "claude-opus-4-5",
    "claude-opus-4-6": "claude-opus-4-6",
    "claude-opus-4-7": "claude-opus-4-7",
    "claude-opus-4-8": "claude-opus-4-8",
    "claude-sonnet-4-5": "claude-sonnet-4-5",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-fable-5": "claude-fable-5",
    "gemini-2-5-flash": "gemini-2-5-flash",
    "gemini-2-5-pro": "gemini-2-5-pro",
    "gemini-3-flash": "gemini-3-flash",
    "gemini-3-pro": "gemini-3-pro",
    "gemini-3-1-pro": "gemini-3-1-pro",
    "gemini-3-5-flash": "gemini-3-5-flash",
    "gemini-3-5-flash-openai": "gemini-3-5-flash-openai",
    "gpt-codex": "gpt-codex",
}

DISPLAY_TO_CHAT_ID = {
    "claude-haiku-4-5": "claude-haiku-4-5",
    "claude-opus-4-5": "claude-opus-4-5",
    "claude-opus-4-6": "claude-opus-4-6",
    "claude-opus-4-7": "claude-opus-4-7",
    "claude-opus-4-8": "claude-opus-4-8",
    "claude-sonnet-4-5": "claude-sonnet-4-5",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-fable-5": "claude-fable-5",
    "gemini 2.5 flash": "gemini-2-5-flash",
    "gemini 2.5 pro": "gemini-2-5-pro",
    "gemini 3 flash": "gemini-3-flash",
    "gemini 3 pro": "gemini-3-pro",
    "gemini 3.1 pro- openai": "gemini-3-1-pro",
    "gemini 3.5 flash": "gemini-3-5-flash",
}


def fetch_json(url: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "KieAI-Sidecar/1.0", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fetch_all_pricing() -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        r = fetch_json(
            "https://api.kie.ai/client/v1/model-pricing/page",
            method="POST",
            body={"pageNum": page, "pageSize": 100},
        )
        if r.get("code") != 200:
            raise RuntimeError(f"pricing page failed: {r}")
        batch = r["data"]["records"]
        rows.extend(batch)
        if len(rows) >= r["data"]["total"]:
            break
        page += 1
    return rows


def model_from_anchor(anchor: str) -> str | None:
    m = re.search(r"model=([^&]+)", anchor or "")
    return unquote(m.group(1)) if m else None


def path_from_anchor(anchor: str) -> str | None:
    if not anchor:
        return None
    parsed = urlparse(anchor)
    return parsed.path.strip("/") or None


def normalize_chat_id(text: str) -> str | None:
    t = text.strip().lower().replace(" ", "-")
    for k, v in DISPLAY_TO_CHAT_ID.items():
        if k.replace(" ", "-") == t or v == t:
            return v
    if t in CHAT_PATH_MAP:
        return t
    m = re.match(r"^(gpt-[\d.a-z-]+|claude-[a-z0-9.-]+|gemini-[a-z0-9.-]+)$", t)
    return t if m else None


def infer_model_field(row: dict, known_paths: set[str]) -> str:
    desc = row["modelDescription"]
    first = desc.split(",")[0].strip()

    if "codex" in first.lower():
        return re.sub(r"\s+", "-", first.strip().lower())

    anchor = row.get("anchor") or ""
    from_model = model_from_anchor(anchor)
    if from_model:
        return from_model

    if "/" in first and not first.startswith("http"):
        return first.strip()

    iface = row["interfaceType"]
    if iface == "chat":
        path_slug = path_from_anchor(anchor)
        if path_slug and path_slug in CHAT_PATH_MAP:
            return CHAT_PATH_MAP[path_slug]
        cid = normalize_chat_id(first)
        if cid:
            return cid
        if path_slug:
            return path_slug.replace("/", "-")

    # Fuzzy match against known paths
    fl = first.lower()
    for p in sorted(known_paths, key=len, reverse=True):
        if p.lower() in fl or fl in p.lower():
            return p
        base = p.split("/")[-1].lower()
        if base and base in fl:
            return p

    return first.lower().replace(" ", "-")


def infer_template(model_field: str, iface: str, desc: str) -> str:
    lower = f"{model_field} {desc}".lower()
    if iface == "chat":
        return "chat"
    if iface == "music":
        return "audio"
    if "upscale" in lower and iface == "image":
        return "image_upscale"
    if "remove-background" in lower or "remove background" in lower:
        return "image_remove_bg"
    if iface == "image":
        if any(x in lower for x in ("image-to-image", "image to image", "edit", "remix", "reframe")):
            return "image_i2i"
        return "image_t2i"
    if iface == "video":
        if "upscale" in lower:
            return "video_upscale"
        if any(x in lower for x in ("image-to-video", "image to video", "i2v", "first frame")):
            return "video_i2v"
        if any(
            x in lower
            for x in (
                "video-to-video",
                "video edit",
                "extend",
                "lip sync",
                "lip-sync",
                "reference-to-video",
                "motion-control",
                "motion control",
            )
        ):
            return "video_v2v"
        if any(x in lower for x in ("speech-to-video", "from-audio", "avatar", "omnihuman", "infinitalk")):
            return "video_audio_avatar"
        return "video_t2v"
    return "generic_jobs"


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9/_.-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s.replace("/", "-")


def build_entry(row: dict, idx: int, known_paths: set[str]) -> dict:
    iface = row["interfaceType"]
    category = {"music": "audio"}.get(iface, iface)
    model_field = infer_model_field(row, known_paths)
    desc = row["modelDescription"]
    template = infer_template(model_field, iface, desc)

    anchor = row.get("anchor") or ""
    docs_path = path_from_anchor(anchor)
    docs_url = f"https://kie.ai/{docs_path}" if docs_path else "https://docs.kie.ai/market/quickstart.md"

    # Unique registry id per pricing row (343 total)
    anchor_model = model_from_anchor(anchor)
    variant = ",".join(desc.split(",")[1:]).strip() if "," in desc else ""
    if anchor_model and variant:
        reg_id = slugify(f"{anchor_model}-{variant}")
    elif anchor_model:
        reg_id = slugify(anchor_model)
    else:
        reg_id = slugify(desc)

    if not reg_id:
        reg_id = f"{category}-{idx}"

    try:
        credits = float(str(row.get("creditPrice", "0")).replace(",", ""))
    except ValueError:
        credits = 10.0

    unit = row.get("creditUnit", "")
    price_hint = f"~{credits} кр. {unit}".strip()

    return {
        "id": reg_id,
        "category": category,
        "display_name": desc,
        "model_field": model_field,
        "template": template,
        "docs_url": docs_url,
        "api_type": "jobs" if category in ("image", "video") else category,
        "price_hint": price_hint,
        "estimate_credits": credits,
        "provider": row.get("provider", ""),
        "pricing_index": idx,
    }


def main() -> None:
    paths_resp = fetch_json("https://api.kie.ai/api/v1/playground/model-paths")
    known_paths = set(paths_resp.get("data") or [])
    pricing = fetch_all_pricing()

    entries = [build_entry(row, i, known_paths) for i, row in enumerate(pricing, 1)]

    # Ensure unique ids
    seen: dict[str, int] = {}
    for e in entries:
        base = e["id"]
        n = seen.get(base, 0) + 1
        seen[base] = n
        if n > 1:
            e["id"] = f"{base}-{n}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    from collections import Counter

    c = Counter(e["category"] for e in entries)
    print(f"Wrote {len(entries)} entries to {OUT}")
    for cat, n in sorted(c.items()):
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
