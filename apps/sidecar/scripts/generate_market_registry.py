#!/usr/bin/env python3
"""Generate registry JSON for chat/image/video from unique model catalog."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "market_manifest.json"
CHAT_DIR = ROOT / "kie_sidecar" / "models" / "registry" / "chat"
IMAGE_DIR = ROOT / "kie_sidecar" / "models" / "registry" / "image"
VIDEO_DIR = ROOT / "kie_sidecar" / "models" / "registry" / "video"

SKIP_CATEGORIES = {"audio", "suno"}
SKIP_API_TYPES = set()  # all jobs for now

PARAMS: dict[str, list[dict]] = {
    "image_t2i": [
        {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
        {"name": "aspect_ratio", "type": "select", "options": ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"], "default": "1:1"},
        {"name": "resolution", "type": "select", "options": ["1K", "2K"], "default": "1K"},
        {"name": "nsfw_checker", "type": "switch", "default": True},
    ],
    "image_i2i": [
        {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
        {"name": "input_urls", "type": "image_urls", "required": True, "max_items": 2},
        {"name": "aspect_ratio", "type": "select", "options": ["1:1", "16:9", "9:16", "4:3", "3:4"], "default": "1:1"},
        {"name": "resolution", "type": "select", "options": ["1K", "2K"], "default": "1K"},
    ],
    "image_upscale": [
        {"name": "image_url", "type": "image_url", "required": True},
        {"name": "scale", "type": "select", "options": ["2", "4"], "default": "2"},
    ],
    "image_remove_bg": [
        {"name": "image_url", "type": "image_url", "required": True},
    ],
    "video_t2v": [
        {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
        {"name": "aspect_ratio", "type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"},
        {"name": "duration", "type": "select", "options": ["5", "10"], "default": "5"},
        {"name": "sound", "type": "switch", "default": False},
    ],
    "video_i2v": [
        {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
        {"name": "image_url", "type": "image_url", "required": True},
        {"name": "aspect_ratio", "type": "select", "options": ["16:9", "9:16", "1:1"], "default": "16:9"},
        {"name": "duration", "type": "select", "options": ["5", "10"], "default": "5"},
    ],
    "video_v2v": [
        {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
        {"name": "video_url", "type": "text", "required": True},
    ],
    "video_upscale": [
        {"name": "video_url", "type": "text", "required": True},
        {"name": "scale", "type": "select", "options": ["2", "4"], "default": "2"},
    ],
    "video_audio_avatar": [
        {"name": "prompt", "type": "textarea", "required": False, "max_length": 2000},
        {"name": "image_url", "type": "image_url", "required": True},
        {"name": "audio_url", "type": "text", "required": True},
    ],
    "generic_jobs": [
        {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
    ],
}

CHAT_DEFAULTS = {
    "claude": {
        "api_path": "/claude/v1/messages",
        "api_style": "claude",
        "supports_vision": True,
        "supports_tools": True,
        "default_params": {"max_tokens": 4096},
        "price_hint": "~0.3 кр/1K tokens",
        "estimate_credits": 5,
    },
    "gemini": {
        "api_path_template": "/{id}/v1/chat/completions",
        "api_style": "openai",
        "supports_vision": True,
        "supports_tools": True,
        "default_params": {"reasoning_effort": "low"},
        "price_hint": "~0.15 кр/1K tokens",
        "estimate_credits": 3,
    },
    "gpt": {
        "api_path_template": "/{id}/v1/chat/completions",
        "api_style": "openai",
        "supports_vision": True,
        "supports_tools": True,
        "default_params": {"reasoning_effort": "medium"},
        "price_hint": "~0.2 кр/1K tokens",
        "estimate_credits": 4,
    },
    "codex": {
        "api_path_template": "/{id}/v1/chat/completions",
        "api_style": "openai",
        "supports_vision": False,
        "supports_tools": True,
        "default_params": {},
        "price_hint": "~0.2 кр/1K tokens",
        "estimate_credits": 4,
    },
}


def slugify(model_id: str) -> str:
    return model_id.replace("/", "-").replace(".", "-")


def chat_family(chat_id: str) -> str:
    if "codex" in chat_id:
        return "codex"
    if chat_id.startswith("claude"):
        return "claude"
    if chat_id.startswith("gemini"):
        return "gemini"
    return "gpt"


def estimate_credits(category: str, template: str) -> tuple[str, float]:
    if category == "image":
        if template in ("image_upscale", "image_remove_bg"):
            return "~10 кр.", 10
        return "~15 кр.", 15
    if category == "video":
        if template == "video_upscale":
            return "~50 кр.", 50
        if template == "video_audio_avatar":
            return "~120 кр.", 120
        return "~100 кр.", 100
    return "~5 кр.", 5


def build_chat(entry: dict) -> dict:
    chat_id = entry["id"]
    family = chat_family(chat_id)
    base = CHAT_DEFAULTS[family]
    api_path = base.get("api_path") or base["api_path_template"].format(id=chat_id)
    return {
        "id": chat_id,
        "display_name": entry["display_name"],
        "api_path": api_path,
        "api_style": base["api_style"],
        "model_field": chat_id,
        "price_hint": base["price_hint"],
        "estimate_credits": base["estimate_credits"],
        "supports_vision": base["supports_vision"],
        "supports_tools": base["supports_tools"],
        "default_params": base["default_params"],
        "docs_url": entry.get("docs_url"),
    }


def build_jobs(entry: dict, category: str) -> dict:
    template = entry.get("template", "generic_jobs")
    price_hint, credits = estimate_credits(category, template)
    model_id = entry["id"]
    return {
        "id": model_id,
        "category": category,
        "display_name": entry["display_name"],
        "api_type": "jobs",
        "create_path": "/api/v1/jobs/createTask",
        "model_field": entry.get("model_field") or model_id,
        "price_hint": price_hint,
        "estimate_credits": credits,
        "parameters": PARAMS.get(template, PARAMS["generic_jobs"]),
        "docs_url": entry.get("docs_url"),
    }


def write_model(path: Path, data: dict, replace: bool) -> bool:
    if path.exists() and not replace:
        return False
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def clear_dir(directory: Path) -> None:
    for path in directory.glob("*.json"):
        path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true", help="Replace all chat/image/video registry JSON")
    args = parser.parse_args()

    if not CATALOG.exists():
        raise SystemExit(f"Run build_market_manifest.py first — missing {CATALOG}")

    if args.replace:
        for d in (CHAT_DIR, IMAGE_DIR, VIDEO_DIR):
            clear_dir(d)

    entries = json.loads(CATALOG.read_text(encoding="utf-8"))
    created = {"chat": 0, "image": 0, "video": 0}
    skipped = 0

    for entry in entries:
        cat = entry["category"]
        if cat in SKIP_CATEGORIES or entry.get("api_type") in SKIP_API_TYPES:
            skipped += 1
            continue
        if not re.match(r"^[a-z0-9][a-z0-9/_.-]*$", entry["id"], re.I):
            skipped += 1
            continue

        if cat == "chat":
            path = CHAT_DIR / f"{slugify(entry['id'])}.json"
            if write_model(path, build_chat(entry), args.replace):
                created["chat"] += 1
        elif cat == "image":
            path = IMAGE_DIR / f"{slugify(entry['id'])}.json"
            if write_model(path, build_jobs(entry, "image"), args.replace):
                created["image"] += 1
        elif cat == "video":
            path = VIDEO_DIR / f"{slugify(entry['id'])}.json"
            if write_model(path, build_jobs(entry, "video"), args.replace):
                created["video"] += 1

    for d in (CHAT_DIR, IMAGE_DIR, VIDEO_DIR):
        count = len(list(d.glob("*.json")))
        print(f"{d.name}: {count} files")

    print(f"Created/updated: {created}, skipped: {skipped}")


if __name__ == "__main__":
    main()
