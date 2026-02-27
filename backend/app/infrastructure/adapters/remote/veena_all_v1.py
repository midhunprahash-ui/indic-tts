from __future__ import annotations

from app.domain.entities import ConfigField, ModelCapabilities
from app.infrastructure.adapters.remote.common import RemoteSelfHostedAdapterBase


class RemoteVeenaAllV1Adapter(RemoteSelfHostedAdapterBase):
    model_id = "maya-research/veena-all-v1"
    display_name = "maya-research/veena-all-v1"
    capabilities = ModelCapabilities(streaming_available=False, supports_prompt_style=True)
    config_schema = [
        ConfigField(
            key="prompt",
            label="Prosody Prompt",
            input_type="textarea",
            default="Clear Indian English cadence with light expressiveness.",
        )
    ]

