from __future__ import annotations

from app.domain.entities import ConfigField, ConfigFieldOption, ModelCapabilities
from app.infrastructure.adapters.self_hosted.common import SelfHostedAdapterBase


class VeenaAllV1Adapter(SelfHostedAdapterBase):
    model_id = "maya-research/veena-all-v1"
    display_name = "maya-research/veena-all-v1"
    capabilities = ModelCapabilities(streaming_available=False, supports_prompt_style=True)
    config_schema = [
        ConfigField(
            key="prompt",
            label="Style Prompt (Optional)",
            input_type="textarea",
            default="Clear Indian English cadence with light expressiveness.",
        ),
        ConfigField(
            key="speaker",
            label="Speaker",
            input_type="select",
            default="kavya",
            options=[
                ConfigFieldOption(label="Kavya", value="kavya"),
                ConfigFieldOption(label="Agastya", value="agastya"),
                ConfigFieldOption(label="Maitri", value="maitri"),
                ConfigFieldOption(label="Vinaya", value="vinaya"),
            ],
        ),
        ConfigField(
            key="temperature",
            label="Temperature",
            input_type="slider",
            default=0.4,
            min=0.1,
            max=1.0,
            step=0.05,
        ),
        ConfigField(
            key="top_p",
            label="Top P",
            input_type="slider",
            default=0.9,
            min=0.5,
            max=1.0,
            step=0.05,
        ),
        ConfigField(
            key="max_new_tokens",
            label="Max New Tokens",
            input_type="number",
            default=700,
            min=128,
            max=2048,
            step=64,
            help_text="700 follows model-card guidance for full sentence generation.",
        ),
    ]
