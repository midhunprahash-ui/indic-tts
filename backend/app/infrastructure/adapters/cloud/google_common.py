from __future__ import annotations

import base64
from typing import Any

from app.domain.entities import AdapterAudio, ConfigField, ConfigFieldOption, ModelCapabilities
from app.domain.errors import DependencyMissingError, ModelUnavailableError, ProviderAuthError
from app.infrastructure.adapters.base import BaseAdapter


class GoogleCloudAdapterBase(BaseAdapter):
    provider = "google"
    category = "cloud"
    capabilities = ModelCapabilities(streaming_available=True, supports_speed=True, supports_pitch=True)
    required_settings_fields = ["google_application_credentials"]
    config_schema = [
        ConfigField(
            key="voice_name",
            label="Voice Name Override",
            input_type="text",
            default="",
            placeholder="Optional full Google voice name",
            help_text="Leave empty to use model default or automatic fallback voice.",
        ),
        ConfigField(
            key="audio_encoding",
            label="Audio Encoding",
            input_type="select",
            default="MP3",
            options=[ConfigFieldOption(label="MP3", value="MP3"), ConfigFieldOption(label="LINEAR16", value="LINEAR16")],
        ),
        ConfigField(key="speaking_rate", label="Speaking Rate", input_type="slider", default=1.0, min=0.25, max=2.0, step=0.05),
        ConfigField(key="pitch", label="Pitch", input_type="slider", default=0.0, min=-20.0, max=20.0, step=0.5),
    ]

    language_code: str
    voice_name: str

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        requested_voice_name = str(config.get("voice_name") or self.voice_name)
        if prefer_streaming:
            try:
                audio = await self._streaming_synthesize(text, config, requested_voice_name)
                if audio:
                    return audio
            except Exception:  # noqa: BLE001
                pass
        return await self._rest_synthesize(text, config, requested_voice_name)

    async def _streaming_synthesize(self, text: str, config: dict[str, Any], voice_name: str) -> AdapterAudio:
        try:
            from google.cloud import texttospeech_v1beta1 as tts_beta
        except ImportError as exc:
            raise DependencyMissingError("google-cloud-texttospeech dependency missing") from exc

        encoding = str(config.get("audio_encoding", "MP3")).upper()
        audio_encoding = getattr(tts_beta.AudioEncoding, encoding, tts_beta.AudioEncoding.MP3)
        voice = tts_beta.VoiceSelectionParams(language_code=self.language_code, name=voice_name)
        stream_config = tts_beta.StreamingSynthesizeConfig(
            voice=voice,
            audio_config=tts_beta.AudioConfig(
                audio_encoding=audio_encoding,
                speaking_rate=self._coerce_float(config, "speaking_rate", 1.0),
                pitch=self._coerce_float(config, "pitch", 0.0),
            ),
        )
        request_1 = tts_beta.StreamingSynthesizeRequest(streaming_config=stream_config)
        request_2 = tts_beta.StreamingSynthesizeRequest(input=tts_beta.StreamingSynthesisInput(text=text))

        def _sync_stream_call() -> bytes:
            client = tts_beta.TextToSpeechClient()
            responses = client.streaming_synthesize(iter([request_1, request_2]))
            chunks: list[bytes] = []
            for response in responses:
                audio_chunk = getattr(response, "audio_content", None)
                if audio_chunk:
                    chunks.append(audio_chunk)
                elif getattr(response, "audio_chunk", None) and getattr(response.audio_chunk, "audio_content", None):
                    chunks.append(response.audio_chunk.audio_content)
            return b"".join(chunks)

        import asyncio

        chunked = await asyncio.to_thread(_sync_stream_call)
        if not chunked:
            raise ModelUnavailableError("Google streaming synth produced no audio")
        ext = "mp3" if encoding == "MP3" else "wav"
        return AdapterAudio(audio_bytes=chunked, audio_format=ext, streaming_used=True)

    async def _rest_synthesize(self, text: str, config: dict[str, Any], voice_name: str) -> AdapterAudio:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
        except ImportError as exc:
            raise DependencyMissingError("google-auth dependency missing") from exc

        credentials_path = self.settings.google_application_credentials
        if not credentials_path:
            raise ProviderAuthError("GOOGLE_APPLICATION_CREDENTIALS is not set")

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        credentials.refresh(Request())

        token = credentials.token
        response = await self._request_rest_synthesize(token=token, text=text, config=config, voice_name=voice_name)

        if response.status_code == 400 and self._is_voice_not_found(response):
            fallback_voice = await self._resolve_fallback_voice(token=token, requested_voice=voice_name)
            if fallback_voice:
                response = await self._request_rest_synthesize(
                    token=token,
                    text=text,
                    config=config,
                    voice_name=fallback_voice,
                )
            else:
                # Last resort: ask Google for language-only default voice.
                response = await self._request_rest_synthesize(
                    token=token,
                    text=text,
                    config=config,
                    voice_name=None,
                )

        if response.status_code in {401, 403}:
            raise ProviderAuthError("Google TTS authentication failed. Verify service account permissions")
        if response.status_code >= 400:
            raise ModelUnavailableError(f"Google TTS error {response.status_code}: {response.text[:300]}")

        data = response.json()
        audio_content = data.get("audioContent")
        if not audio_content:
            raise ModelUnavailableError("Google TTS returned no audio content")

        try:
            decoded = base64.b64decode(audio_content)
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError("Google TTS returned invalid audio content") from exc

        ext = "mp3" if str(config.get("audio_encoding", "MP3")).upper() == "MP3" else "wav"
        return AdapterAudio(audio_bytes=decoded, audio_format=ext, streaming_used=False)

    async def _request_rest_synthesize(
        self,
        token: str,
        text: str,
        config: dict[str, Any],
        voice_name: str | None,
    ):
        voice_payload: dict[str, str] = {"languageCode": self.language_code}
        if voice_name:
            voice_payload["name"] = voice_name

        payload = {
            "input": {"text": text},
            "voice": voice_payload,
            "audioConfig": {
                "audioEncoding": str(config.get("audio_encoding", "MP3")).upper(),
                "speakingRate": self._coerce_float(config, "speaking_rate", 1.0),
                "pitch": self._coerce_float(config, "pitch", 0.0),
            },
        }
        return await self.http_client.post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    async def _resolve_fallback_voice(self, token: str, requested_voice: str) -> str | None:
        response = await self.http_client.get(
            "https://texttospeech.googleapis.com/v1/voices",
            headers={"Authorization": f"Bearer {token}"},
            params={"languageCode": self.language_code},
        )
        if response.status_code >= 400:
            return None
        names = [
            voice.get("name")
            for voice in (response.json().get("voices") or [])
            if isinstance(voice, dict) and isinstance(voice.get("name"), str)
        ]
        if not names:
            return None

        requested_lower = requested_voice.lower()
        base_lower = requested_voice.rsplit("-", 1)[0].lower() if "-" in requested_voice else requested_lower
        language_prefix = f"{self.language_code.lower()}-"
        candidates: list[str] = []

        def add_if(match_fn):
            for name in names:
                if match_fn(name.lower()) and name not in candidates:
                    candidates.append(name)

        add_if(lambda n: n == requested_lower)
        add_if(lambda n: n.startswith(f"{requested_lower}-"))
        add_if(lambda n: n.startswith(base_lower))

        if "chirp3" in requested_lower:
            add_if(lambda n: "chirp3-hd" in n)
        if "neural2" in requested_lower:
            add_if(lambda n: "neural2" in n)

        add_if(lambda n: n.startswith(language_prefix))
        return candidates[0] if candidates else None

    @staticmethod
    def _is_voice_not_found(response) -> bool:
        try:
            message = str(response.json().get("error", {}).get("message", "")).lower()
        except Exception:  # noqa: BLE001
            message = response.text.lower()
        return "voice" in message and "does not exist" in message
