from __future__ import annotations

from typing import Any

from app.domain.entities import AdapterAudio, ConfigField, ConfigFieldOption, ModelCapabilities
from app.domain.errors import ModelUnavailableError, ProviderAuthError
from app.infrastructure.adapters.base import BaseAdapter


class ElevenLabsAdamIndianAdapter(BaseAdapter):
    model_id = "elevenlabs:Adam-Indian-accent"
    display_name = "ElevenLabs - Adam (Indian accent)"
    provider = "elevenlabs"
    category = "cloud"
    capabilities = ModelCapabilities(streaming_available=True, supports_speed=True, supports_pitch=False)
    required_settings_fields = ["elevenlabs_api_key"]
    config_schema = [
        ConfigField(
            key="model_id",
            label="Model",
            input_type="select",
            default="eleven_multilingual_v2",
            options=[
                ConfigFieldOption(label="Eleven Multilingual v2", value="eleven_multilingual_v2"),
                ConfigFieldOption(label="Eleven Turbo v2.5", value="eleven_turbo_v2_5"),
            ],
        ),
        ConfigField(
            key="output_format",
            label="Output Format",
            input_type="select",
            default="mp3_44100_128",
            options=[
                ConfigFieldOption(label="MP3 44.1kHz 128kbps", value="mp3_44100_128"),
                ConfigFieldOption(label="MP3 22.05kHz 32kbps", value="mp3_22050_32"),
            ],
        ),
        ConfigField(key="stability", label="Stability", input_type="slider", default=0.35, min=0, max=1, step=0.05),
        ConfigField(
            key="similarity_boost",
            label="Similarity Boost",
            input_type="slider",
            default=0.75,
            min=0,
            max=1,
            step=0.05,
        ),
        ConfigField(key="style", label="Style", input_type="slider", default=0.2, min=0, max=1, step=0.05),
        ConfigField(key="speed", label="Speed", input_type="slider", default=1.0, min=0.7, max=1.2, step=0.05),
        ConfigField(
            key="voice_id",
            label="Voice ID Override",
            input_type="text",
            default="",
            placeholder="Optional custom Adam voice ID",
            help_text="If empty, ELEVENLABS_ADAM_VOICE_ID from env is used.",
        ),
    ]

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        voice_id = str(config.get("voice_id") or self.settings.elevenlabs_adam_voice_id or "").strip()
        if not voice_id:
            raise ModelUnavailableError("ElevenLabs voice_id is missing. Set ELEVENLABS_ADAM_VOICE_ID or provide override.")

        model_id = str(config.get("model_id", self.settings.elevenlabs_model_id))
        output_format = str(config.get("output_format", "mp3_44100_128"))
        voice_settings = {
            "stability": self._coerce_float(config, "stability", 0.35),
            "similarity_boost": self._coerce_float(config, "similarity_boost", 0.75),
            "style": self._coerce_float(config, "style", 0.2),
            "use_speaker_boost": True,
            "speed": self._coerce_float(config, "speed", 1.0),
        }

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings,
        }

        if prefer_streaming:
            try:
                audio = await self._request_audio(
                    endpoint=f"/v1/text-to-speech/{voice_id}/stream",
                    payload=payload,
                    output_format=output_format,
                )
                return AdapterAudio(audio_bytes=audio, audio_format="mp3", streaming_used=True)
            except Exception:  # noqa: BLE001
                pass

        audio = await self._request_audio(
            endpoint=f"/v1/text-to-speech/{voice_id}",
            payload=payload,
            output_format=output_format,
        )
        return AdapterAudio(audio_bytes=audio, audio_format="mp3", streaming_used=False)

    async def _request_audio(self, endpoint: str, payload: dict[str, Any], output_format: str) -> bytes:
        response = await self.http_client.post(
            f"{self.settings.elevenlabs_base_url.rstrip('/')}{endpoint}",
            params={"output_format": output_format},
            headers={
                "xi-api-key": self.settings.elevenlabs_api_key or "",
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json=payload,
        )

        if response.status_code in {401, 403}:
            provider_detail = self._extract_detail(response.text)
            raise ProviderAuthError(f"ElevenLabs authentication failed. {provider_detail}")
        if response.status_code >= 400:
            raise ModelUnavailableError(f"ElevenLabs error {response.status_code}: {response.text[:300]}")
        if not response.content:
            raise ModelUnavailableError("ElevenLabs returned empty audio")
        return response.content

    @staticmethod
    def _extract_detail(raw_text: str) -> str:
        try:
            import json

            data = json.loads(raw_text)
            detail = data.get("detail", {})
            status = detail.get("status")
            message = detail.get("message")
            if status and message:
                return f"{status}: {message}"
            if message:
                return str(message)
        except Exception:  # noqa: BLE001
            pass
        return raw_text[:220] or "Check API key permissions and account limits."
