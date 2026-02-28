from __future__ import annotations

from app.infrastructure.adapters.cloud.azure_common import AzureAdapterBase, build_azure_config_schema


class AzureEnINNeerjaAdapter(AzureAdapterBase):
    model_id = "azure:en-IN-NeerjaNeural"
    display_name = "Microsoft Azure - en-IN-NeerjaNeural"
    voice_name = "en-IN-NeerjaNeural"
    locale = "en-IN"
    config_schema = build_azure_config_schema(default_locale=locale, default_voice_name=voice_name)
