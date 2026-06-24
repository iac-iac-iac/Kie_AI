from __future__ import annotations

from pathlib import Path
from typing import Literal

MediaType = Literal["image", "video", "audio"]


class MediaStore:
    def __init__(self, images_dir: Path, videos_dir: Path, audio_dir: Path) -> None:
        self._images_dir = images_dir
        self._videos_dir = videos_dir
        self._audio_dir = audio_dir
        self._images_dir.mkdir(parents=True, exist_ok=True)
        self._videos_dir.mkdir(parents=True, exist_ok=True)
        self._audio_dir.mkdir(parents=True, exist_ok=True)

    def _dir_for(self, media_type: MediaType) -> Path:
        if media_type == "video":
            return self._videos_dir
        if media_type == "audio":
            return self._audio_dir
        return self._images_dir

    def resolve_local_path(
        self,
        generation_id: str,
        media_type: MediaType,
        extension: str,
    ) -> Path:
        default_ext = {
            "video": "mp4",
            "audio": "mp3",
            "image": "png",
        }[media_type]
        ext = extension or default_ext
        return self._dir_for(media_type) / f"{generation_id}.{ext}"

    def save_image(self, generation_id: str, data: bytes, extension: str = "png") -> Path:
        path = self.resolve_local_path(generation_id, "image", extension)
        path.write_bytes(data)
        return path

    def delete_file(self, path: str | Path | None) -> None:
        if not path:
            return
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()

    def guess_extension(
        self,
        url: str,
        content_type: str | None = None,
        media_type: MediaType = "image",
    ) -> str:
        if content_type:
            if "mpeg" in content_type or "mp3" in content_type:
                return "mp3"
            if "wav" in content_type:
                return "wav"
            if "ogg" in content_type:
                return "ogg"
            if "mp4" in content_type:
                return "mp4"
            if "webm" in content_type:
                return "webm"
            if "quicktime" in content_type or "mov" in content_type:
                return "mov"
            if "jpeg" in content_type or "jpg" in content_type:
                return "jpg"
            if "webp" in content_type:
                return "webp"
            if "png" in content_type:
                return "png"
        lower = url.lower().split("?")[0]
        if media_type == "audio":
            for ext in ("mp3", "wav", "ogg", "m4a", "mp4"):
                if lower.endswith(f".{ext}"):
                    return "mp3" if ext == "m4a" else ext
            return "mp3"
        if media_type == "video":
            for ext in ("mp4", "webm", "mov"):
                if lower.endswith(f".{ext}"):
                    return ext
            return "mp4"
        for ext in ("jpg", "jpeg", "webp", "png"):
            if lower.endswith(f".{ext}"):
                return "jpg" if ext == "jpeg" else ext
        return "png"
