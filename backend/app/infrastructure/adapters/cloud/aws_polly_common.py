from __future__ import annotations

import asyncio
import html
from typing import Any

from app.domain.entities import AdapterAudio, ConfigField, ConfigFieldOption, ModelCapabilities
from app.domain.errors import DependencyMissingError, ModelUnavailableError, ProviderAuthError
from app.infrastructure.adapters.base import BaseAdapter


def build_aws_polly_config_schema(default_language_code: str, default_voice_id: str) -> list[ConfigField]:
    return [
        ConfigField(
            key="language_code",
            label="Language Code",
            input_type="text",
            default=default_language_code,
            help_text="Polly language code used with the selected voice.",
        ),
        ConfigField(
            key="voice_id",
            label="Voice ID",
            input_type="text",
            default=default_voice_id,
            help_text="AWS Polly voice id (example: Seema, Ramya).",
        ),
        ConfigField(
            key="engine",
            label="Engine",
            input_type="select",
            default="neural",
            options=[
                ConfigFieldOption(label="Neural", value="neural"),
                ConfigFieldOption(label="Standard", value="standard"),
            ],
        ),
        ConfigField(
            key="output_format",
            label="Output Format",
            input_type="select",
            default="mp3",
            options=[
                ConfigFieldOption(label="MP3", value="mp3"),
                ConfigFieldOption(label="OGG Vorbis", value="ogg_vorbis"),
            ],
        ),
        ConfigField(
            key="speaking_rate",
            label="Speaking Rate",
            input_type="slider",
            default=1.0,
            min=0.5,
            max=2.0,
            step=0.05,
        ),
        ConfigField(
            key="pitch",
            label="Pitch",
            input_type="slider",
            default=0,
            min=-20,
            max=20,
            step=1,
            help_text="Applied via SSML prosody when non-zero.",
        ),
    ]


class AWSPollyAdapterBase(BaseAdapter):
    provider = "aws"
    category = "cloud"
    capabilities = ModelCapabilities(streaming_available=False, supports_speed=True, supports_pitch=True)
    required_settings_fields = ["aws_access_key_id", "aws_secret_access_key", "aws_region"]
    config_schema: list[ConfigField] = []

    voice_id: str
    language_code: str

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        _ = prefer_streaming

        output_format = str(config.get("output_format", "mp3"))
        engine = str(config.get("engine", "neural"))
        voice_id = str(config.get("voice_id") or self.voice_id)
        language_code = str(config.get("language_code") or self.language_code)
        speaking_rate = self._coerce_float(config, "speaking_rate", 1.0)
        pitch = self._coerce_int(config, "pitch", 0)
        text_payload, text_type = self._build_text_payload(text=text, speaking_rate=speaking_rate, pitch=pitch)

        audio_bytes = await asyncio.to_thread(
            self._synthesize_sync,
            text_payload,
            text_type,
            output_format,
            engine,
            voice_id,
            language_code,
        )

        audio_ext = "mp3" if output_format == "mp3" else "ogg"
        return AdapterAudio(audio_bytes=audio_bytes, audio_format=audio_ext, streaming_used=False)

    def _synthesize_sync(
        self,
        text_payload: str,
        text_type: str,
        output_format: str,
        engine: str,
        voice_id: str,
        language_code: str,
    ) -> bytes:
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError as exc:
            raise DependencyMissingError("boto3 is required for AWS Polly adapters") from exc

        client = boto3.client(
            "polly",
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            aws_session_token=self.settings.aws_session_token,
            region_name=self.settings.aws_region,
        )

        try:
            response = client.synthesize_speech(
                Text=text_payload,
                TextType=text_type,
                VoiceId=voice_id,
                LanguageCode=language_code,
                Engine=engine,
                OutputFormat=output_format,
            )
            stream = response.get("AudioStream")
            if stream is None:
                raise ModelUnavailableError("AWS Polly returned no audio stream")
            data = stream.read()
            stream.close()
            if not data:
                raise ModelUnavailableError("AWS Polly returned empty audio")
            return data
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            message = exc.response.get("Error", {}).get("Message", str(exc))
            if code in {"UnrecognizedClientException", "InvalidSignatureException", "AccessDeniedException"}:
                raise ProviderAuthError(f"AWS Polly auth failed: {message}") from exc
            raise ModelUnavailableError(f"AWS Polly error ({code}): {message}") from exc
        except BotoCoreError as exc:
            raise ModelUnavailableError(f"AWS Polly runtime error: {exc}") from exc

    @staticmethod
    def _build_text_payload(text: str, speaking_rate: float, pitch: int) -> tuple[str, str]:
        if speaking_rate == 1.0 and pitch == 0:
            return text, "text"

        rate_pct = int((speaking_rate - 1.0) * 100)
        rate_attr = f"{rate_pct:+d}%"
        pitch_attr = f"{pitch:+d}%"
        safe_text = html.escape(text)
        ssml = (
            "<speak><prosody "
            f"rate='{rate_attr}' pitch='{pitch_attr}'>"
            f"{safe_text}"
            "</prosody></speak>"
        )
        return ssml, "ssml"
