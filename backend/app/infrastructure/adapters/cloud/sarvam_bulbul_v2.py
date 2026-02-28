from __future__ import annotations

import asyncio
import json
from typing import Any

from app.domain.entities import AdapterAudio, ConfigField, ConfigFieldOption, ModelCapabilities
from app.domain.errors import ModelUnavailableError, ProviderAuthError
from app.infrastructure.adapters.base import BaseAdapter
from app.infrastructure.adapters.cloud.common import decode_base64_audio


class SarvamBulbulV2Adapter(BaseAdapter):
    model_id = "sarvam:bulbul:v2"
    display_name = "Sarvam AI - bulbul:v2"
    provider = "sarvam"
    category = "cloud"
    capabilities = ModelCapabilities(streaming_available=True, supports_speed=True, supports_pitch=True)
    required_settings_fields = ["sarvam_api_key"]
    config_schema = [
        ConfigField(
            key="target_language_code",
            label="Target Language",
            input_type="select",
            default="ta-IN",
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
        if prefer_streaming:
            try:
                return await self._synthesize_streaming(text, config)
            except Exception:  # noqa: BLE001
                # Automatic fallback to REST when streaming is unavailable or fails.
                pass
        return await self._synthesize_rest(text, config)

    async def _synthesize_streaming(self, text: str, config: dict[str, Any]) -> AdapterAudio:
        try:
            import websockets
        except ImportError as exc:
            raise ModelUnavailableError("websockets dependency missing for Sarvam streaming") from exc

        language = str(config.get("target_language_code", "ta-IN"))
        speaker = str(config.get("speaker", "anushka"))
        pace = self._coerce_float(config, "pace", 1.0)
        pitch = self._coerce_float(config, "pitch", 0.0)
        codec = str(config.get("audio_format", "mp3"))
        ws_url = "wss://api.sarvam.ai/text-to-speech/ws?model=bulbul:v2&send_completion_event=true"

        chunks: list[bytes] = []
        async with websockets.connect(ws_url, additional_headers={"Api-Subscription-Key": self.settings.sarvam_api_key or ""}) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "config",
                        "data": {
                            "target_language_code": language,
                            "speaker": speaker,
                            "pace": pace,
                            "pitch": pitch,
                            "output_audio_codec": codec,
                        },
                    }
                )
            )
            await ws.send(json.dumps({"type": "text", "data": {"text": text}}))
            await ws.send(json.dumps({"type": "flush"}))

            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=15)
                except TimeoutError:
                    break
                if raw is None:
                    break
                payload = json.loads(raw)
                msg_type = payload.get("type")
                if msg_type == "audio":
                    audio_b64 = (
                        payload.get("data", {}).get("audio")
                        or payload.get("data", {}).get("chunk")
                        or payload.get("chunk")
                    )
                    if audio_b64:
                        chunks.append(decode_base64_audio(audio_b64))
                elif msg_type == "event":
                    event_name = payload.get("data", {}).get("event_type") or payload.get("data", {}).get("name")
                    if event_name in {"final", "generation_finished"}:
                        break
                elif msg_type == "error":
                    raise ModelUnavailableError(payload.get("data", {}).get("message", "Sarvam streaming error"))

        if not chunks:
            raise ModelUnavailableError("No streaming audio chunks received from Sarvam")
        return AdapterAudio(audio_bytes=b"".join(chunks), audio_format=codec if codec in {"wav", "mp3"} else "mp3", streaming_used=True)

    async def _synthesize_rest(self, text: str, config: dict[str, Any]) -> AdapterAudio:
        url = f"{self.settings.sarvam_base_url.rstrip('/')}/text-to-speech/convert"
        audio_format = str(config.get("audio_format", "WAV")).upper()
        payload = {
            "text": text,
            "target_language_code": str(config.get("target_language_code", "ta-IN")),
            "model": "bulbul:v2",
            "speaker": str(config.get("speaker", "anushka")),
            "audio_format": audio_format,
        }
        response = await self.http_client.post(
            url,
            headers={"Api-Subscription-Key": self.settings.sarvam_api_key or "", "Content-Type": "application/json"},
            json=payload,
        )

        if response.status_code in {401, 403}:
            raise ProviderAuthError("Sarvam authentication failed. Check SARVAM_API_KEY")
        if response.status_code >= 400:
            raise ModelUnavailableError(f"Sarvam error {response.status_code}: {response.text[:300]}")

        data = response.json()
        audios = data.get("audios") or []
        if not audios:
            raise ModelUnavailableError("Sarvam returned no audio payload")
        audio_bytes = decode_base64_audio(audios[0])
        ext = "mp3" if audio_format == "MP3" else "wav"
        return AdapterAudio(audio_bytes=audio_bytes, audio_format=ext, streaming_used=False)
