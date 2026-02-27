from __future__ import annotations

from app.infrastructure.adapters.cloud.azure_common import AzureAdapterBase


class AzureEnINNeerjaAdapter(AzureAdapterBase):
    model_id = "azure:en-IN-NeerjaNeural"
    display_name = "Microsoft Azure - en-IN-NeerjaNeural"
    voice_name = "en-IN-NeerjaNeural"
    locale = "en-IN"
