from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_timeout_seconds: int = 45
    max_concurrent_synth: int = 6
    request_timeout_seconds: int = 35
    backend_role: str = "all_local"

    # Sarvam
    sarvam_api_key: str | None = None
    sarvam_base_url: str = "https://api.sarvam.ai"

    # Google
    google_application_credentials: str | None = None
    google_tts_project_id: str | None = None

    # Azure
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None

    # AWS Polly
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    aws_region: str = "ap-south-1"

    # ElevenLabs
    elevenlabs_api_key: str | None = None
    elevenlabs_base_url: str = "https://api.elevenlabs.io"
    elevenlabs_adam_voice_id: str = "pNInz6obpgDQGcFmaJgB"
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    # HF / local inference
    hf_token: str | None = None
    hf_home: str | None = None
    hf_cache_dir: str | None = None
    local_device: str = "cpu"
    local_dtype: str = "float32"
    local_model_warmup: bool = False
    local_model_timeout_seconds: int = 900

    # Remote self-hosted worker routing (Lightning)
    remote_self_hosted_url: str | None = None
    remote_self_hosted_timeout_seconds: int = 120

    # alias overrides
    hf_alias_maya_research_veena_all_v1: str = "maya-research/Veena"

    audio_store_dir: str = "/tmp/tanglish_tts_audio"
    public_audio_base_url: str = "http://localhost:8000"

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def audio_dir_path(self) -> Path:
        return Path(self.audio_store_dir)


settings = Settings()
