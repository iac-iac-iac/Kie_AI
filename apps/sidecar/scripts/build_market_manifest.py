#!/usr/bin/env python3
"""Build full model catalog from docs.kie.ai llms.txt."""
from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "catalog" / "market_manifest.json"
LLMS_URL = "https://docs.kie.ai/llms.txt"

SKIP = re.compile(
    r"\b("
    r"Get |Callback|record-info|Quickstart|validate-info|check-voice|Webhook|"
    r"Details|Download URL|Direct Download|Base64|File Stream|URL File|"
    r"regenerate|Human Identification|Subject Detection|remaining|"
    r"Integration Guide|Claude Code"
    r")\b",
    re.I,
)

CHAT_PATH_MAP = {
    "market/chat/gpt-5-2.md": "gpt-5-2",
    "market/chat/gpt-5-4.md": "gpt-5-4",
    "market/chat/gpt-5-5.md": "gpt-5-5",
    "market/claude/claude-opus-4-7.md": "claude-opus-4-7",
    "market/claude/claude-opus-4-8.md": "claude-opus-4-8",
    "market/claude/cluade-fable-5.md": "claude-fable-5",
    "market/claude/claude-haiku-4-5.md": "claude-haiku-4-5",
    "market/claude/claude-opus-4-5.md": "claude-opus-4-5",
    "market/claude/claude-opus-4-6.md": "claude-opus-4-6",
    "market/claude/claude-sonnet-4-5.md": "claude-sonnet-4-5",
    "market/claude/claude-sonnet-4-6.md": "claude-sonnet-4-6",
    "market/gemini/gemini-2-5-pro.md": "gemini-2-5-pro",
    "market/gemini/gemini-3-pro.md": "gemini-3-pro",
    "market/gemini/gemini-3-1-pro.md": "gemini-3-1-pro",
    "market/gemini/gemini-2-5-flash.md": "gemini-2-5-flash",
    "market/gemini/gemini-3-flash.md": "gemini-3-flash",
    "market/gemini/gemini-3-5-flash.md": "gemini-3-5-flash",
    "market/gemini/gemini-3-5-flash-openai.md": "gemini-3-5-flash-openai",
    "market/gemini/gemini-3-flash-v1beta.md": "gemini-3-flash-v1beta",
    "market/codex/gpt-codex.md": "gpt-codex",
}

KLING_SLUG_MAP = {
    "text-to-video": "kling-2.6/text-to-video",
    "image-to-video": "kling-2.6/image-to-video",
    "v25-turbo-image-to-video-pro": "kling/v2-5-turbo-image-to-video-pro",
    "v25-turbo-text-to-video-pro": "kling/v2-5-turbo-text-to-video-pro",
    "v2-1-master-image-to-video": "kling/v2-1-master-image-to-video",
    "v2-1-master-text-to-video": "kling/v2-1-master-text-to-video",
    "v2-1-pro": "kling/v2-1-pro",
    "v2-1-standard": "kling/v2-1-standard",
    "v3-turbo-text-to-video": "kling/v3-turbo-text-to-video",
    "v3-turbo-image-to-video": "kling/v3-turbo-image-to-video",
    "motion-control": "kling/motion-control",
    "motion-control-v3": "kling/motion-control-v3",
    "kling-3-0": "kling/kling-3-0",
    "ai-avatar-standard": "kling/ai-avatar-standard",
    "ai-avatar-pro": "kling/ai-avatar-pro",
}

PROVIDER_IDS = {
    "flux2": "flux-2",
    "grok-imagine": "grok-imagine",
    "gpt-image": "gpt-image",
    "gpt": "gpt",
    "google": "google",
    "bytedance": "bytedance",
    "kling": "kling",
    "wan": "wan",
    "hailuo": "hailuo",
    "ideogram": "ideogram",
    "qwen": "qwen",
    "qwen2": "qwen2",
    "seedream": "seedream",
    "topaz": "topaz",
    "recraft": "recraft",
    "happyhorse": "happyhorse",
    "happyhorse-1-1": "happyhorse-1-1",
    "volcengine": "volcengine",
    "elevenlabs": "elevenlabs",
    "infinitalk": "infinitalk",
    "omnihuman-1-5": "omnihuman-1-5",
    "z-image": "z-image",
    "sora2": "sora2",
    "luma": "luma",
    "midjourney": "midjourney",
    "pika": "pika",
    "minimax": "minimax",
}


def fetch_llms() -> str:
    req = urllib.request.Request(LLMS_URL, headers={"User-Agent": "KieAI-Sidecar/1.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")


def norm(line: str) -> str:
    return re.sub(r"\s+", " ", line)


def classify(line: str) -> str:
    n = norm(line)
    if "Image Models" in n:
        return "image"
    if "Video Models" in n:
        return "video"
    if "Chat Models" in n or "Codex" in n:
        return "chat"
    if "Music Models" in n or "ElevenLabs" in n:
        return "audio"
    if "Suno API" in n:
        return "suno"
    if re.search(r"Veo\s*3", n, re.I):
        return "veo"
    if "4o Image API" in n:
        return "image4o"
    if "Flux Kontext" in n:
        return "flux_kontext"
    if "Runway API" in n:
        return "runway"
    return "other"


def path_to_model_id(doc_path: str) -> str | None:
    if doc_path in CHAT_PATH_MAP:
        return CHAT_PATH_MAP[doc_path]

    if doc_path.startswith("market/"):
        rest = doc_path[len("market/") :].replace(".md", "")
        provider, _, slug = rest.partition("/")
        if not slug:
            return provider

        if provider == "codex":
            return f"codex/{slug}"

        prefix = PROVIDER_IDS.get(provider, provider)
        if provider == "kling" and slug in KLING_SLUG_MAP:
            return KLING_SLUG_MAP[slug]
        if provider == "gemini-omni-video":
            return "gemini-omni/video"
        if provider == "gemini-omni-audio":
            return "gemini-omni/audio"
        if doc_path.endswith("gemini-omni-character.md"):
            return "gemini-omni/character"
        return f"{prefix}/{slug}"

    if "generate-4-o-image" in doc_path and "callback" not in doc_path:
        return "4o-image/generate"
    if "generate-or-edit-image" in doc_path and "callback" not in doc_path:
        return "flux-kontext/generate-or-edit"
    if "generate-veo-3-video" in doc_path and "callback" not in doc_path:
        return "veo3.1/generate"
    if "extend-video" in doc_path and "veo" in doc_path and "callback" not in doc_path:
        return "veo3.1/extend"
    if "generate-ai-video" in doc_path and "callback" not in doc_path:
        return "runway/generate"
    if "generate-aleph-video" in doc_path and "callback" not in doc_path:
        return "runway/aleph"
    if "extend-ai-video" in doc_path and "callback" not in doc_path:
        return "runway/extend"

    return None


def infer_template(model_id: str, category: str, line: str) -> str:
    lower = f"{model_id} {line}".lower()
    if category == "chat":
        return "chat"
    if category in ("veo", "runway"):
        if "extend" in lower:
            return "video_v2v"
        return "video_i2v" if "image" in lower else "video_t2v"
    if category == "image4o":
        return "image_t2i"
    if category == "flux_kontext":
        return "image_i2i"
    if "upscale" in lower or "crisp-upscale" in lower:
        return "image_upscale"
    if "remove-background" in lower or "remove-background" in model_id:
        return "image_remove_bg"
    if category == "image":
        if any(x in lower for x in ("image-to-image", "image to image", "edit", "remix", "cover", "inpaint")):
            return "image_i2i"
        return "image_t2i"
    if category == "video":
        if "upscale" in lower:
            return "video_upscale"
        if any(x in lower for x in ("image-to-video", "image to video", "i2v", "first_frame", "first-frame")):
            return "video_i2v"
        if any(
            x in lower
            for x in (
                "video-to-video",
                "video edit",
                "extend",
                "lip-sync",
                "reference-to-video",
                "r2v",
                "motion-control",
                "video-editing",
            )
        ):
            return "video_v2v"
        if any(x in lower for x in ("speech-to-video", "from-audio", "avatar", "omnihuman", "infinitalk", "lip")):
            return "video_audio_avatar"
        return "video_t2v"
    return "generic_jobs"


def display_name(line: str, model_id: str) -> str:
    m = re.match(r"- [^[]+\[([^\]]+)\]", line)
    if m:
        return m.group(1).strip()
    return model_id.replace("/", " ").replace("-", " ").title()


def parse_llms(text: str) -> list[dict]:
    start = text.find("## API Docs")
    if start < 0:
        raise ValueError("## API Docs not found")
    section = text[start:]

    seen: dict[str, dict] = {}
    for line in section.splitlines():
        if not line.startswith("-"):
            continue
        if "/cn/" in line:
            continue
        if SKIP.search(line):
            continue
        m = re.search(r"\]\(https://docs\.kie\.ai/([^)]+)\)", line)
        if not m:
            continue
        doc_path = m.group(1)
        category = classify(line)
        if category in ("suno", "other"):
            continue
        model_id = path_to_model_id(doc_path)
        if not model_id:
            continue
        if not re.match(r"^[a-z0-9][a-z0-9/_.-]*$", model_id):
            continue

        key = f"{category}:{model_id}"
        if key in seen:
            continue
        template = infer_template(model_id, category, line)
        seen[key] = {
            "id": model_id,
            "category": category,
            "display_name": display_name(line, model_id),
            "doc_path": doc_path,
            "docs_url": f"https://docs.kie.ai/{doc_path}",
            "template": template,
            "model_field": model_id,
            "api_type": "jobs"
            if category in ("image", "video", "audio")
            else category,
        }

        if category == "veo":
            seen[key]["api_type"] = "veo"
        elif category == "runway":
            seen[key]["api_type"] = "runway"
        elif category == "image4o":
            seen[key]["api_type"] = "image4o"
        elif category == "flux_kontext":
            seen[key]["api_type"] = "flux_kontext"

    return sorted(seen.values(), key=lambda x: (x["category"], x["id"]))


PATHS_URL = "https://api.kie.ai/api/v1/playground/model-paths"

SKIP_PATHS = {
    "openai/whisper-speech-to-text",
    "kling/v1-tts",
}

SKIP_PREFIXES = (
    "elevenlabs/",
    "ai-music-api/",
    "suno/",
)

CHAT_SINGLE = re.compile(r"^(gpt-|claude-|gemini-).+|.*codex$", re.I)

IMAGE_HINTS = (
    "text-to-image",
    "image-to-image",
    "image-edit",
    "image/upscale",
    "image-upscale",
    "remove-background",
    "crisp-upscale",
    "seedream",
    "imagen4",
    "nano-banana",
    "flux",
    "ideogram",
    "qwen",
    "recraft",
    "gpt-image",
    "character",
    "reframe",
    "remix",
    "/edit",
    "features/flux1-kontext",
    "features/mj-api",
    "kie/image-refiner",
    "grok-imagine/text-to-image",
    "grok-imagine/image-to-image",
    "grok-imagine/upscale",
    "midjourney/vary",
    "midjourney/upscale",
    "wan/2-7-image",
    "z-image",
    "nano-banana-upscale",
)


def fetch_paths() -> list[str]:
    req = urllib.request.Request(PATHS_URL, headers={"User-Agent": "KieAI-Sidecar/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return sorted({p.strip() for p in data["data"] if p and p.strip()})


def categorize_path(path: str) -> str | None:
    pl = path.lower()
    if path in SKIP_PATHS or any(pl.startswith(p) for p in SKIP_PREFIXES):
        return None
    if "/" not in path:
        if CHAT_SINGLE.match(path):
            return "chat"
        if pl in {"nano-banana-2", "nano-banana-pro", "z-image"} or pl.startswith("nano-banana"):
            return "image"
        return "video"
    if any(h in pl for h in IMAGE_HINTS):
        return "image"
    return "video"


def title_case_id(model_id: str) -> str:
    return model_id.replace("/", " / ").replace("-", " ").title()


def slug_key(model_id: str) -> str:
    return model_id.replace("/", "-").replace(".", "-").lower()


def build_unique_catalog() -> list[dict]:
    paths = fetch_paths()
    llms_models = parse_llms(fetch_llms())
    llms_by_id = {m["id"]: m for m in llms_models}
    llms_by_slug = {slug_key(m["id"]): m for m in llms_models}

    entries: list[dict] = []
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()

    for path in paths:
        category = categorize_path(path)
        if category is None:
            continue
        llms = llms_by_id.get(path) or llms_by_slug.get(slug_key(path), {})
        template = llms.get("template") or infer_template(path, category, path)
        entries.append(
            {
                "id": path,
                "category": category,
                "display_name": llms.get("display_name") or title_case_id(path),
                "model_field": path,
                "template": template,
                "docs_url": llms.get("docs_url") or "https://docs.kie.ai/market/quickstart.md",
                "api_type": "jobs" if category in ("image", "video") else category,
            }
        )
        seen_ids.add(path)
        seen_slugs.add(slug_key(path))

    for m in llms_models:
        mid = m["id"]
        if mid in seen_ids or slug_key(mid) in seen_slugs:
            continue
        if m["category"] in ("audio", "suno"):
            continue
        if m["category"] not in ("chat", "image", "video"):
            continue
        entries.append(
            {
                "id": mid,
                "category": m["category"],
                "display_name": m["display_name"],
                "model_field": m.get("model_field") or mid,
                "template": m.get("template", "generic_jobs"),
                "docs_url": m.get("docs_url"),
                "api_type": m.get("api_type", "jobs"),
            }
        )
        seen_ids.add(mid)
        seen_slugs.add(slug_key(mid))

    return sorted(entries, key=lambda x: (x["category"], x["id"]))


def main() -> None:
    models = build_unique_catalog()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(models, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    c = Counter(m["category"] for m in models)
    print(f"Wrote {len(models)} unique models to {OUT}")
    for cat, n in sorted(c.items()):
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
