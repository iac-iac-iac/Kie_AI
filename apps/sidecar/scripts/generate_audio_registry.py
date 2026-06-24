#!/usr/bin/env python3
"""Generate all 24 audio model registry JSON files."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "kie_sidecar" / "models" / "registry" / "audio"

CUSTOM_STYLE = {
    "visible_when": {"custom_mode": True},
    "required_when": {"custom_mode": True},
}
CUSTOM_TITLE = {
    "visible_when": {"custom_mode": True},
    "required_when": {"custom_mode": True},
}
EXTEND_STYLE = {
    "visible_when": {"default_param_flag": True},
    "required_when": {"default_param_flag": True},
}
EXTEND_TITLE = {
    "visible_when": {"default_param_flag": True},
    "required_when": {"default_param_flag": True},
}
EXTEND_CONTINUE = {
    "visible_when": {"default_param_flag": True},
    "required_when": {"default_param_flag": True},
}


def music_params(prompt_max: int, style_max: int) -> list[dict]:
    return [
        {"name": "prompt", "type": "textarea", "required": True, "max_length": prompt_max},
        {"name": "instrumental", "type": "switch", "default": True},
        {"name": "custom_mode", "type": "switch", "default": False},
        {
            "name": "style",
            "type": "textarea",
            "required": False,
            "max_length": style_max,
            **CUSTOM_STYLE,
        },
        {"name": "title", "type": "text", "required": False, "max_length": 80, **CUSTOM_TITLE},
        {"name": "negative_tags", "type": "text", "required": False, "max_length": 500},
    ]


MUSIC_MODELS = [
    ("suno-v3-5", "suno/v3-5", "Suno V3.5", "V3_5", 50, 3000, 200),
    ("suno-v4", "suno/v4", "Suno V4", "V4", 60, 3000, 200),
    ("suno-v4-5", "suno/v4-5", "Suno V4.5", "V4_5", 80, 5000, 1000),
    ("suno-v4-5-plus", "suno/v4-5-plus", "Suno V4.5 Plus", "V4_5PLUS", 100, 5000, 1000),
    ("suno-v4-5-all", "suno/v4-5-all", "Suno V4.5 All", "V4_5ALL", 90, 5000, 1000),
    ("suno-v5", "suno/v5", "Suno V5", "V5", 120, 5000, 1000),
    ("suno-v5-5", "suno/v5-5", "Suno V5.5", "V5_5", 130, 5000, 1000),
]

UPLOAD_MUSIC_PARAMS = [
    {"name": "upload_url", "type": "text", "required": True},
    {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
    {"name": "instrumental", "type": "switch", "default": True},
    {"name": "custom_mode", "type": "switch", "default": False},
    {
        "name": "style",
        "type": "textarea",
        "required": False,
        "max_length": 1000,
        **CUSTOM_STYLE,
    },
    {"name": "title", "type": "text", "required": False, "max_length": 80, **CUSTOM_TITLE},
    {"name": "negative_tags", "type": "text", "required": False, "max_length": 500},
]

TTS_PARAMS = [
    {"name": "text", "type": "textarea", "required": True, "max_length": 5000},
    {"name": "voice", "type": "text", "required": True, "default": "Rachel"},
]


def write(filename: str, data: dict) -> None:
    path = OUT / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  {filename}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    for slug, model_id, name, field, credits, prompt_max, style_max in MUSIC_MODELS:
        write(
            f"{slug}.json",
            {
                "id": model_id,
                "category": "audio",
                "display_name": name,
                "api_type": "suno",
                "operation": "generate",
                "model_field": field,
                "output_kind": "audio",
                "price_hint": f"~{credits} кр.",
                "estimate_credits": credits,
                "parameters": music_params(prompt_max, style_max),
                "docs_url": "https://docs.kie.ai/suno-api/generate-music",
            },
        )

    write(
        "suno-lyrics.json",
        {
            "id": "suno/lyrics",
            "category": "audio",
            "display_name": "Suno Generate Lyrics",
            "api_type": "suno",
            "operation": "lyrics",
            "model_field": "",
            "output_kind": "text",
            "price_hint": "~10 кр.",
            "estimate_credits": 10,
            "parameters": [
                {"name": "prompt", "type": "textarea", "required": True, "max_length": 200},
            ],
            "docs_url": "https://docs.kie.ai/suno-api/generate-lyrics",
        },
    )

    write(
        "suno-extend.json",
        {
            "id": "suno/extend",
            "category": "audio",
            "display_name": "Suno Extend Music",
            "api_type": "suno",
            "operation": "extend",
            "model_field": "V4_5",
            "output_kind": "audio",
            "price_hint": "~80 кр.",
            "estimate_credits": 80,
            "parameters": [
                {"name": "audio_id", "type": "text", "required": True},
                {"name": "default_param_flag", "type": "switch", "default": True},
                {"name": "prompt", "type": "textarea", "required": False, "max_length": 5000},
                {
                    "name": "style",
                    "type": "textarea",
                    "required": False,
                    "max_length": 1000,
                    **EXTEND_STYLE,
                },
                {"name": "title", "type": "text", "required": False, "max_length": 80, **EXTEND_TITLE},
                {
                    "name": "continue_at",
                    "type": "number",
                    "required": False,
                    **EXTEND_CONTINUE,
                },
                {"name": "negative_tags", "type": "text", "required": False, "max_length": 500},
                {
                    "name": "vocal_gender",
                    "type": "select",
                    "required": False,
                    "options": ["m", "f"],
                },
            ],
            "docs_url": "https://docs.kie.ai/suno-api/extend-music",
        },
    )

    for slug, op, name, credits in [
        ("suno-upload-cover", "upload_cover", "Suno Upload & Cover", 90),
        ("suno-upload-extend", "upload_extend", "Suno Upload & Extend", 90),
    ]:
        write(
            f"{slug}.json",
            {
                "id": f"suno/{slug.replace('suno-', '')}",
                "category": "audio",
                "display_name": name,
                "api_type": "suno",
                "operation": op,
                "model_field": "V4_5",
                "output_kind": "audio",
                "price_hint": f"~{credits} кр.",
                "estimate_credits": credits,
                "parameters": UPLOAD_MUSIC_PARAMS,
                "docs_url": f"https://docs.kie.ai/suno-api/{slug.replace('suno-', '').replace('-', '-')}",
            },
        )

    write(
        "suno-add-instrumental.json",
        {
            "id": "suno/add-instrumental",
            "category": "audio",
            "display_name": "Suno Add Instrumental",
            "api_type": "suno",
            "operation": "add_instrumental",
            "model_field": "V4_5",
            "output_kind": "audio",
            "price_hint": "~70 кр.",
            "estimate_credits": 70,
            "parameters": [
                {"name": "upload_url", "type": "text", "required": True},
                {"name": "title", "type": "text", "required": True, "max_length": 80},
                {"name": "tags", "type": "text", "required": True, "max_length": 500},
                {"name": "negative_tags", "type": "text", "required": True, "max_length": 500},
            ],
            "docs_url": "https://docs.kie.ai/suno-api/add-instrumental",
        },
    )

    write(
        "suno-add-vocals.json",
        {
            "id": "suno/add-vocals",
            "category": "audio",
            "display_name": "Suno Add Vocals",
            "api_type": "suno",
            "operation": "add_vocals",
            "model_field": "V4_5",
            "output_kind": "audio",
            "price_hint": "~70 кр.",
            "estimate_credits": 70,
            "parameters": [
                {"name": "upload_url", "type": "text", "required": True},
                {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
                {"name": "title", "type": "text", "required": True, "max_length": 80},
                {"name": "style", "type": "textarea", "required": True, "max_length": 1000},
            ],
            "docs_url": "https://docs.kie.ai/suno-api/add-vocals",
        },
    )

    for slug, op, name, credits in [
        ("suno-convert-wav", "convert_wav", "Suno Convert to WAV", 20),
        ("suno-music-video", "music_video", "Suno Music Video", 50),
        ("suno-midi", "midi", "Suno MIDI", 30),
    ]:
        write(
            f"{slug}.json",
            {
                "id": f"suno/{slug.replace('suno-', '')}",
                "category": "audio",
                "display_name": name,
                "api_type": "suno",
                "operation": op,
                "model_field": "",
                "output_kind": "audio",
                "price_hint": f"~{credits} кр.",
                "estimate_credits": credits,
                "parameters": [
                    {"name": "task_id", "type": "text", "required": True},
                    {"name": "audio_id", "type": "text", "required": True},
                ],
                "docs_url": f"https://docs.kie.ai/suno-api/{slug.replace('suno-', '').replace('-', '-')}",
            },
        )

    write(
        "suno-separate-vocals.json",
        {
            "id": "suno/separate-vocals",
            "category": "audio",
            "display_name": "Suno Separate Vocals",
            "api_type": "suno",
            "operation": "separate_vocals",
            "model_field": "",
            "output_kind": "audio",
            "price_hint": "~40 кр.",
            "estimate_credits": 40,
            "parameters": [
                {"name": "task_id", "type": "text", "required": True},
                {"name": "audio_id", "type": "text", "required": True},
                {
                    "name": "type",
                    "type": "select",
                    "required": False,
                    "default": "separate_vocal",
                    "options": ["separate_vocal", "split_stem"],
                },
            ],
            "docs_url": "https://docs.kie.ai/suno-api/separate-vocals",
        },
    )

    write(
        "suno-boost-style.json",
        {
            "id": "suno/boost-style",
            "category": "audio",
            "display_name": "Suno Boost Style",
            "api_type": "suno",
            "operation": "boost_style",
            "model_field": "",
            "output_kind": "text",
            "price_hint": "~5 кр.",
            "estimate_credits": 5,
            "parameters": [
                {"name": "content", "type": "textarea", "required": True, "max_length": 1000},
            ],
            "docs_url": "https://docs.kie.ai/suno-api/boost-music-style",
        },
    )

    write(
        "suno-persona.json",
        {
            "id": "suno/persona",
            "category": "audio",
            "display_name": "Suno Generate Persona",
            "api_type": "suno",
            "operation": "persona",
            "model_field": "",
            "output_kind": "metadata",
            "sync_result": True,
            "price_hint": "~10 кр.",
            "estimate_credits": 10,
            "parameters": [
                {"name": "task_id", "type": "text", "required": True},
                {"name": "audio_id", "type": "text", "required": True},
                {"name": "name", "type": "text", "required": True, "max_length": 80},
                {"name": "description", "type": "textarea", "required": True, "max_length": 500},
                {"name": "style", "type": "textarea", "required": False, "max_length": 1000},
                {"name": "vocal_start", "type": "number", "required": False},
                {"name": "vocal_end", "type": "number", "required": False},
            ],
            "docs_url": "https://docs.kie.ai/suno-api/generate-persona",
        },
    )

    write(
        "suno-generate-sounds.json",
        {
            "id": "suno/generate-sounds",
            "category": "audio",
            "display_name": "Suno Generate Sounds",
            "api_type": "suno",
            "operation": "generate_sounds",
            "model_field": "",
            "output_kind": "audio",
            "price_hint": "~30 кр.",
            "estimate_credits": 30,
            "parameters": [
                {"name": "prompt", "type": "textarea", "required": True, "max_length": 5000},
            ],
            "docs_url": "https://docs.kie.ai/suno-api/quickstart",
        },
    )

    for slug, model_id, name, credits in [
        ("elevenlabs-tts-multilingual-v2", "elevenlabs/text-to-speech-multilingual-v2", "ElevenLabs TTS Multilingual v2", 15),
        ("elevenlabs-tts-turbo-2-5", "elevenlabs/text-to-speech-turbo-2-5", "ElevenLabs TTS Turbo 2.5", 10),
        ("elevenlabs-dialogue-v3", "elevenlabs/text-to-dialogue-v3", "ElevenLabs Dialogue v3", 20),
        ("elevenlabs-audio-isolation", "elevenlabs/audio-isolation", "ElevenLabs Audio Isolation", 15),
    ]:
        params = TTS_PARAMS if "isolation" not in slug else [
            {"name": "audio_url", "type": "text", "required": True},
        ]
        write(
            f"{slug}.json",
            {
                "id": model_id,
                "category": "audio",
                "display_name": name,
                "api_type": "jobs",
                "operation": "generate",
                "model_field": model_id,
                "output_kind": "audio",
                "price_hint": f"~{credits} кр.",
                "estimate_credits": credits,
                "parameters": params,
                "docs_url": f"https://docs.kie.ai/market/{model_id}",
            },
        )

    count = len(list(OUT.glob("*.json")))
    print(f"\nTotal: {count} models")


if __name__ == "__main__":
    main()
