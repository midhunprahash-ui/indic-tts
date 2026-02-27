from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ModelCategory = Literal["cloud", "self_hosted"]


class ConfigFieldOption(BaseModel):
    label: str
    value: str


class ConfigField(BaseModel):
    key: str
    label: str
    input_type: Literal["text", "textarea", "number", "select", "checkbox", "slider"]
    required: bool = False
    default: Any = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[ConfigFieldOption] = Field(default_factory=list)
    placeholder: str | None = None
    help_text: str | None = None


class ModelCapabilities(BaseModel):
    streaming_available: bool = False
    supports_speed: bool = False
    supports_pitch: bool = False
    supports_prompt_style: bool = False


class ConfigStatus(BaseModel):
    configured: bool
    warnings: list[str] = Field(default_factory=list)


class AdapterAudio(BaseModel):
    audio_bytes: bytes
    audio_format: Literal["wav", "mp3", "ogg", "flac"] = "wav"
    streaming_used: bool = False


class ModelCatalogItem(BaseModel):
    model_id: str
    display_name: str
    provider: str
    category: ModelCategory
    capabilities: ModelCapabilities
    config_schema: list[ConfigField]
    configured: bool
    config_warnings: list[str]
    runtime_alias: str | None = None


class SynthesisResult(BaseModel):
    model_id: str
    success: bool
    audio_base64: str | None = None
    audio_url: str | None = None
    latency_ms: int
    streaming_used: bool
    error: str | None = None
