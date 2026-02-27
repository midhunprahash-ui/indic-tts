from __future__ import annotations

from typing import Any

from app.domain.entities import AdapterAudio, ConfigField, ConfigFieldOption, ModelCapabilities
from app.domain.errors import ModelUnavailableError, ProviderAuthError
from app.infrastructure.adapters.base import BaseAdapter
from app.infrastructure.adapters.cloud.common import decode_base64_audio
from app.infrastructure.adapters.cloud.sarvam_bulbul_v2 import SarvamBulbulV2Adapter


class SarvamBulbulV3BetaAdapter(BaseAdapter):
    model_id = "sarvam:bulbul:v3-beta"
    display_name = "Sarvam AI - bulbul:v3-beta"
    provider = "sarvam"
    category = "cloud"
    capabilities = ModelCapabilities(streaming_available=False, supports_speed=True, supports_pitch=True)
    required_settings_fields = ["sarvam_api_key"]
    config_schema = [
        ConfigField(
            key="target_language_code",
            label="Target Language",
            input_type="select",
            default="en-IN",
            options=[
                ConfigFieldOption(label="English (India)", value="en-IN"),
                ConfigFieldOption(label="Tamil (India)", value="ta-IN"),
                ConfigFieldOption(label="Hindi (India)", value="hi-IN"),
            ],
        ),
        ConfigField(
            key="speaker",
            label="Speaker",
            input_type="select",
            default="anushka",
            options=[
                ConfigFieldOption(label="Anushka", value="anushka"),
                ConfigFieldOption(label="Manisha", value="manisha"),
                ConfigFieldOption(label="Arya", value="arya"),
            ],
        ),
        ConfigField(key="pace", label="Speed", input_type="slider", default=1.0, min=0.5, max=2.0, step=0.1),
        ConfigField(key="pitch", label="Pitch", input_type="slider", default=0.0, min=-1.0, max=1.0, step=0.1),
        ConfigField(
            key="audio_format",
            label="Audio Format",
            input_type="select",
            default="mp3",
            options=[ConfigFieldOption(label="MP3", value="mp3"), ConfigFieldOption(label="WAV", value="wav")],
        ),
    ]

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        _ = prefer_streaming
        url = f"{self.settings.sarvam_base_url.rstrip('/')}/text-to-speech/convert"
        audio_format = str(config.get("audio_format", "WAV")).upper()
        payload_base = {
            "text": text,
            "target_language_code": str(config.get("target_language_code", "en-IN")),
            "speaker": str(config.get("speaker", "anushka")),
            "audio_format": audio_format,
        }

        response = await self.http_client.post(
            url,
            headers={"Api-Subscription-Key": self.settings.sarvam_api_key or "", "Content-Type": "application/json"},
            json={**payload_base, "model": "bulbul:v3-beta"},
        )

        if response.status_code == 404:
            # v3-beta is not available for many accounts yet; fallback through v2 adapter.
            v2_adapter = SarvamBulbulV2Adapter(self.settings, self.http_client)
            return await v2_adapter.synthesize(text=text, config=config, prefer_streaming=True)

        if response.status_code in {401, 403}:
            raise ProviderAuthError("Sarvam authentication failed. Check SARVAM_API_KEY")
        if response.status_code >= 400:
            raise ModelUnavailableError(
                f"Sarvam bulbul:v3-beta unavailable ({response.status_code}). This may require account/model access: {response.text[:260]}"
            )

        data = response.json()
        audios = data.get("audios") or []
        if not audios:
            raise ModelUnavailableError("Sarvam returned no audio payload for bulbul:v3-beta")
        audio_bytes = decode_base64_audio(audios[0])
        ext = "mp3" if audio_format == "MP3" else "wav"
        return AdapterAudio(audio_bytes=audio_bytes, audio_format=ext, streaming_used=False)
