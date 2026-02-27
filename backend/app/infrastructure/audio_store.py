from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.infrastructure.config.settings import Settings


class AudioStore:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._base_dir = settings.audio_dir_path()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, audio_bytes: bytes, extension: str) -> str:
        audio_id = f"{uuid4().hex}.{extension}"
        path = self._base_dir / audio_id
        path.write_bytes(audio_bytes)
        return audio_id

    def to_url(self, audio_id: str) -> str:
        return f"{self._settings.public_audio_base_url.rstrip('/')}/tts/audio/{audio_id}"

    def serve(self, audio_id: str) -> FileResponse:
        path = self._base_dir / audio_id
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Audio not found")
        media_type = "audio/mpeg" if audio_id.endswith(".mp3") else "audio/wav"
        return FileResponse(path, media_type=media_type, filename=audio_id)
