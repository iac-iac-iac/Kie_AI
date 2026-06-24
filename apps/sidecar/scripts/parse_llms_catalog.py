#!/usr/bin/env python3
"""Parse docs.kie.ai llms.txt into a model catalog manifest."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

LLMS_URL = "https://docs.kie.ai/llms.txt"
OUT = Path(__file__).resolve().parents[1] / "catalog" / "llms_models.json"

SKIP_PATTERN = re.compile(
    r"\b("
    r"Get |Details|Callback|Download URL|Direct Download|record-info|"
    r"Get Task|Get Music|Get Lyrics|Get WAV|Get Vocal|Get Cover|Get MIDI|"
    r"Get Aleph|Get AI Video|Get 4o|Get Image Details|Get Remaining|"
    r"Base64|File Stream|URL File|Webhook|validate-info|check-voice|"
    r"regenerate|Get Timestamped|Get Cover Generation|Get MIDI Generation|"
    r"Get Vocal Separation|Get Music Video|Get Lyrics Task|Get WAV Conversion|"
    r"Get Direct Download|Human Identification|Subject Detection"
    r")\b",
    re.I,
)

USING_ID = re.compile(
    r"(?:using|by)\s+([a-z0-9][a-z0-9/_\-.]+)",
    re.I,
)


def classify(line: str) -> str:
    if "Image Models" in line:
        return "image"
    if "Video Models" in line:
        return "video"
    if "Chat Models" in line or "Codex" in line:
        return "chat"
    if "Music Models" in line or "ElevenLabs" in line:
        return "audio"
    if "Suno API" in line:
        return "suno"
    if "Veo" in line:
        return "veo"
    if "4o Image API" in line:
        return "image4o"
    if "Flux Kontext API" in line:
        return "flux_kontext"
    if "Runway API" in line:
        return "runway"
    return "other"


def path_to_model_id(doc_path: str, line: str) -> str | None:
    explicit = USING_ID.search(line)
    if explicit:
        return explicit.group(1).rstrip(".")

    if doc_path.startswith("market/"):
        rest = doc_path[len("market/") :].replace(".md", "")
        provider, _, slug = rest.partition("/")
        if not slug:
            return provider

        provider_ids = {
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
        }
        prefix = provider_ids.get(provider, provider)

        kling_slug_map = {
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
        if provider == "kling" and slug in kling_slug_map:
            return kling_slug_map[slug]

        if provider == "gemini-omni-video":
            return "gemini-omni/video"
        if provider == "gemini-omni-audio":
            return "gemini-omni/audio"
        if doc_path.endswith("gemini-omni-character.md"):
            return "gemini-omni/character"

        return f"{prefix}/{slug}"

    if doc_path.startswith("market/") is False:
        if "generate-4-o-image" in doc_path:
            return "4o-image/generate"
        if "generate-or-edit-image" in doc_path:
            return "flux-kontext/generate-or-edit"
        if "generate-veo-3-video" in doc_path:
            return "veo3.1/generate"
        if "generate-ai-video" in doc_path:
            return "runway/generate"
        if "generate-aleph-video" in doc_path:
            return "runway/aleph"
        if "extend-ai-video" in doc_path:
            return "runway/extend"
        if "extend-video" in doc_path and "veo" in doc_path:
            return "veo3.1/extend"

    chat_map = {
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
    if doc_path in chat_map:
        return chat_map[doc_path]

    return None


def infer_template(model_id: str, category: str, line: str) -> str:
    lower = f"{model_id} {line}".lower()
    if category == "chat":
        return "chat"
    if "upscale" in lower or "crisp-upscale" in lower:
        return "image_upscale"
    if "remove-background" in lower:
        return "image_remove_bg"
    if category == "image":
        if any(x in lower for x in ("image-to-image", "image to image", "edit", "remix", "cover")):
            return "image_i2i"
        return "image_t2i"
    if category == "video":
        if "upscale" in lower:
            return "video_upscale"
        if any(x in lower for x in ("image-to-video", "image to video", "i2v", "图生视频", "图转视频")):
            return "video_i2v"
        if any(x in lower for x in ("video-to-video", "video edit", "extend", "lip-sync", "reference-to-video", "r2v")):
            return "video_v2v"
        if any(x in lower for x in ("speech-to-video", "from-audio", "avatar", "omnihuman", "lip")):
            return "video_audio_avatar"
        return "video_t2v"
    return "generic_jobs"


def parse_llms(text: str) -> list[dict]:
    start = text.find("## API Docs")
    if start < 0:
        raise ValueError("API Docs section not found")
    end = text.find("- Image Models > Seedream [Seedream3.0 生成图像]")
    section = text[start:end] if end > start else text[start:]

    seen: dict[str, dict] = {}
    for line in section.splitlines():
        if not line.startswith("- "):
            continue
        if "/cn/" in line:
            continue
        if SKIP_PATTERN.search(line):
            continue
        m = re.search(r"\]\(https://docs\.kie\.ai/([^)]+)\)", line)
        if not m:
            continue
        doc_path = m.group(1)
        category = classify(line)
        if category in ("suno", "other"):
            continue
        model_id = path_to_model_id(doc_path, line)
        if not model_id:
            continue
        title_m = re.match(r"- [^[]+\[([^\]]+)\]", line)
        display_name = title_m.group(1).strip() if title_m else model_id
        key = f"{category}:{model_id}"
        if key in seen:
            continue
        seen[key] = {
            "id": model_id,
            "category": category,
            "display_name": display_name,
            "doc_path": doc_path,
            "docs_url": f"https://docs.kie.ai/{doc_path}",
            "template": infer_template(model_id, category, line),
            "model_field": model_id,
        }
    return sorted(seen.values(), key=lambda x: (x["category"], x["id"]))


def main() -> None:
    text = urllib.request.urlopen(LLMS_URL, timeout=60).read().decode("utf-8")
    models = parse_llms(text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(models, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from collections import Counter

    c = Counter(m["category"] for m in models)
    print(f"Wrote {len(models)} models to {OUT}")
    print(dict(c))


if __name__ == "__main__":
    main()
