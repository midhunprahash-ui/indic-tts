from __future__ import annotations

from app.domain.entities import ConfigField, ModelCapabilities
from app.infrastructure.adapters.self_hosted.common import SelfHostedAdapterBase


class VeenaAllV1Adapter(SelfHostedAdapterBase):
    model_id = "maya-research/veena-all-v1"
    display_name = "maya-research/veena-all-v1"
    capabilities = ModelCapabilities(streaming_available=False, supports_prompt_style=True)
    config_schema = [
        ConfigField(
            key="prompt",
            label="Prosody Prompt",
            input_type="textarea",
            default="Clear Indian English cadence with light expressiveness.",
        ),
        ConfigField(
            key="max_new_tokens",
            label="Max New Tokens",
            input_type="number",
            default=256,
            min=64,
            max=2048,
            step=32,
            help_text="Use higher values for longer sentences if the model reports max_length errors.",
        ),
    ]
