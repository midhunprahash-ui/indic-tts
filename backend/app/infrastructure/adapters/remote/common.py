from __future__ import annotations

import base64
from typing import Any

from app.domain.entities import AdapterAudio
from app.domain.errors import ModelUnavailableError
from app.infrastructure.adapters.base import BaseAdapter


class RemoteSelfHostedAdapterBase(BaseAdapter):
    provider = "lightning-ai"
    category = "self_hosted"
    required_settings_fields = ["remote_self_hosted_url"]

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        base_url = (self.settings.remote_self_hosted_url or "").rstrip("/")
        url = f"{base_url}/tts/synthesize"

        payload = {
            "model_id": self.model_id,
            "text": text,
            "config_overrides": config,
            "prefer_streaming": prefer_streaming,
        }
        timeout = self.settings.remote_self_hosted_timeout_seconds

        try:
            response = await self.http_client.post(url, json=payload, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"Remote self-hosted backend unavailable: {exc}") from exc

        if response.status_code >= 400:
            body = response.text.strip()
            raise ModelUnavailableError(
                f"Remote self-hosted backend error {response.status_code}: {body[:500]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ModelUnavailableError("Remote self-hosted backend returned invalid JSON") from exc

        result = data.get("result")
        if not isinstance(result, dict):
            raise ModelUnavailableError("Remote self-hosted backend returned malformed payload")

        if not result.get("success"):
            message = str(result.get("error") or "Remote self-hosted synthesis failed")
            raise ModelUnavailableError(message)

        audio_base64 = result.get("audio_base64")
        if not isinstance(audio_base64, str) or not audio_base64:
            raise ModelUnavailableError("Remote self-hosted backend did not return audio_base64")

        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError("Remote self-hosted audio payload is not valid base64") from exc

        return AdapterAudio(
            audio_bytes=audio_bytes,
            audio_format="wav",
            streaming_used=bool(result.get("streaming_used", False)),
        )

