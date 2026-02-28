from __future__ import annotations

from app.infrastructure.adapters.cloud.azure_common import AzureAdapterBase, build_azure_config_schema


class AzureTaINSwetaAdapter(AzureAdapterBase):
    model_id = "azure:ta-IN-SwetaNeural"
    display_name = "Microsoft Azure - ta-IN-SwetaNeural"
    voice_name = "ta-IN-SwetaNeural"
    locale = "ta-IN"
    config_schema = build_azure_config_schema(default_locale=locale, default_voice_name=voice_name)
