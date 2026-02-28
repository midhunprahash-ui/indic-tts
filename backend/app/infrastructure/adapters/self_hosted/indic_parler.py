from __future__ import annotations

from app.domain.entities import ConfigField, ModelCapabilities
from app.infrastructure.adapters.self_hosted.common import SelfHostedAdapterBase


class IndicParlerAdapter(SelfHostedAdapterBase):
    model_id = "ai4bharat/indic-parler-tts"
    display_name = "ai4bharat/indic-parler-tts"
    capabilities = ModelCapabilities(streaming_available=False, supports_prompt_style=True)
    config_schema = [
        ConfigField(
            key="description",
            label="Speaker Description",
            input_type="textarea",
            default="A warm Tanglish conversational voice with clear Tamil pronunciation.",
            help_text="Used by description-conditioned TTS models such as Parler-style voices.",
        ),
        ConfigField(
            key="prompt",
            label="Style Hints (Optional)",
            input_type="textarea",
            default="",
            help_text="Optional style guidance appended to speaker description. Spoken text always comes from center input.",
        ),
    ]
