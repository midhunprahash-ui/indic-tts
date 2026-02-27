from __future__ import annotations

import base64
from typing import Any

from app.domain.errors import ModelUnavailableError


def decode_base64_audio(data: str) -> bytes:
    try:
        return base64.b64decode(data)
    except Exception as exc:  # noqa: BLE001
        raise ModelUnavailableError("Provider returned invalid base64 audio") from exc


def extract_nested_audio(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("audioContent", "audio", "content", "chunk"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        for value in payload.values():
            found = extract_nested_audio(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = extract_nested_audio(item)
            if found:
                return found
    return None
