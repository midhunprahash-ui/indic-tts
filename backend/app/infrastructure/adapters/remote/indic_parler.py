from __future__ import annotations

from app.domain.entities import ConfigField, ModelCapabilities
from app.infrastructure.adapters.remote.common import RemoteSelfHostedAdapterBase


class RemoteIndicParlerAdapter(RemoteSelfHostedAdapterBase):
    model_id = "ai4bharat/indic-parler-tts"
    display_name = "ai4bharat/indic-parler-tts"
    capabilities = ModelCapabilities(streaming_available=False, supports_prompt_style=True)
    config_schema = [
        ConfigField(
            key="description",
            label="Speaker Description",
            input_type="textarea",
            default="Jaya speaks Tamil with clear pronunciation, moderate pace, and very clear audio.",
            help_text="Voice descriptor used by Indic Parler. Keep this as speaker/style description, not transcript.",
        ),
        ConfigField(
            key="prompt",
            label="Style Hints (Optional)",
            input_type="textarea",
            default="",
            help_text="Optional extra style hints. The center text input is always the spoken transcript.",
        ),
        ConfigField(
            key="max_new_tokens",
            label="Max New Tokens",
            input_type="number",
            default=1024,
            min=128,
            max=4096,
            step=64,
            help_text="Maximum generated audio tokens for this utterance.",
        ),
        ConfigField(
            key="temperature",
            label="Temperature",
            input_type="slider",
            default=1.0,
            min=0.1,
            max=2.0,
            step=0.05,
            help_text="Controls sampling diversity (1.0 = default).",
        ),
    ]
