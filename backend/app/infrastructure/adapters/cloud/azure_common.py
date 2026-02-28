from __future__ import annotations

import asyncio
from typing import Any

from app.domain.entities import AdapterAudio, ConfigField, ConfigFieldOption, ModelCapabilities
from app.domain.errors import DependencyMissingError, ModelUnavailableError, ProviderAuthError
from app.infrastructure.adapters.base import BaseAdapter


def build_azure_config_schema(default_locale: str, default_voice_name: str) -> list[ConfigField]:
    return [
        ConfigField(
            key="locale",
            label="Locale",
            input_type="text",
            default=default_locale,
            help_text="Language locale used in SSML.",
        ),
        ConfigField(
            key="voice_name",
            label="Voice Name",
            input_type="text",
            default=default_voice_name,
            help_text="Azure neural voice name for synthesis.",
        ),
        ConfigField(
            key="style",
            label="Style",
            input_type="text",
            default="",
            placeholder="cheerful, calm, narration-professional",
        ),
        ConfigField(key="rate", label="Rate", input_type="slider", default=1.0, min=0.5, max=2.0, step=0.1),
        ConfigField(key="pitch", label="Pitch", input_type="slider", default=0, min=-20, max=20, step=1),
        ConfigField(
            key="output_format",
            label="Output Format",
            input_type="select",
            default="audio-24khz-48kbitrate-mono-mp3",
            options=[
                ConfigFieldOption(label="MP3 24kHz", value="audio-24khz-48kbitrate-mono-mp3"),
                ConfigFieldOption(label="MP3 16kHz", value="audio-16khz-32kbitrate-mono-mp3"),
            ],
        ),
    ]


class AzureAdapterBase(BaseAdapter):
    provider = "azure"
    category = "cloud"
    capabilities = ModelCapabilities(streaming_available=True, supports_speed=True, supports_pitch=True)
    required_settings_fields = ["azure_speech_key", "azure_speech_region"]
    config_schema: list[ConfigField] = []

    voice_name: str
    locale: str

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        voice_name = str(config.get("voice_name") or self.voice_name)
        locale = str(config.get("locale") or self.locale)
        if prefer_streaming:
            try:
                return await self._sdk_synthesize(text, config, voice_name, locale)
            except Exception:  # noqa: BLE001
                pass
        return await self._rest_synthesize(text, config, voice_name, locale)

    async def _sdk_synthesize(
        self,
        text: str,
        config: dict[str, Any],
        voice_name: str,
        locale: str,
    ) -> AdapterAudio:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as exc:
            raise DependencyMissingError("azure-cognitiveservices-speech dependency missing") from exc

        def _sync_synthesize() -> bytes:
            speech_config = speechsdk.SpeechConfig(
                subscription=self.settings.azure_speech_key,
                region=self.settings.azure_speech_region,
            )
            speech_config.speech_synthesis_voice_name = voice_name
            output_format = str(config.get("output_format", "audio-24khz-48kbitrate-mono-mp3"))
            format_map = {
                "audio-24khz-48kbitrate-mono-mp3": speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3,
                "audio-16khz-32kbitrate-mono-mp3": speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3,
            }
            speech_config.set_speech_synthesis_output_format(
                format_map.get(output_format, speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3)
            )
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            ssml = self._build_ssml(text, config, voice_name, locale)
            result = synthesizer.speak_ssml_async(ssml).get()
            if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
                details = getattr(result, "error_details", "Azure synthesis failed")
                raise ModelUnavailableError(str(details))
            return bytes(result.audio_data)

        audio_bytes = await asyncio.to_thread(_sync_synthesize)
        if not audio_bytes:
            raise ModelUnavailableError("Azure SDK produced empty audio")
        return AdapterAudio(audio_bytes=audio_bytes, audio_format="mp3", streaming_used=True)

    async def _rest_synthesize(
        self,
        text: str,
        config: dict[str, Any],
        voice_name: str,
        locale: str,
    ) -> AdapterAudio:
        region = self.settings.azure_speech_region
        endpoint = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        output_format = str(config.get("output_format", "audio-24khz-48kbitrate-mono-mp3"))
        response = await self.http_client.post(
            endpoint,
            headers={
                "Ocp-Apim-Subscription-Key": self.settings.azure_speech_key or "",
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": output_format,
                "User-Agent": "tanglish-tts-playground",
            },
            content=self._build_ssml(text, config, voice_name, locale).encode("utf-8"),
        )

        if response.status_code in {401, 403}:
            raise ProviderAuthError("Azure auth failed. Check AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")
        if response.status_code >= 400:
            raise ModelUnavailableError(f"Azure TTS error {response.status_code}: {response.text[:300]}")

        audio = response.content
        if not audio:
            raise ModelUnavailableError("Azure returned empty audio")
        return AdapterAudio(audio_bytes=audio, audio_format="mp3", streaming_used=False)

    def _build_ssml(self, text: str, config: dict[str, Any], voice_name: str, locale: str) -> str:
        style = str(config.get("style", "")).strip()
        rate = self._coerce_float(config, "rate", 1.0)
        rate_pct = int((rate - 1.0) * 100)
        prosody_rate = f"{rate_pct:+d}%"
        pitch = self._coerce_int(config, "pitch", 0)
        prosody_pitch = f"{pitch:+d}%"

        if style:
            return (
                "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
                "xmlns:mstts='https://www.w3.org/2001/mstts' "
                f"xml:lang='{locale}'>"
                f"<voice name='{voice_name}'>"
                f"<mstts:express-as style='{style}'>"
                f"<prosody rate='{prosody_rate}' pitch='{prosody_pitch}'>{text}</prosody>"
                "</mstts:express-as>"
                "</voice>"
                "</speak>"
            )

        return (
            "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
            f"xml:lang='{locale}'>"
            f"<voice name='{voice_name}'>"
            f"<prosody rate='{prosody_rate}' pitch='{prosody_pitch}'>{text}</prosody>"
            "</voice>"
            "</speak>"
        )
