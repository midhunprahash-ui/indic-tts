from __future__ import annotations

from app.infrastructure.adapters.cloud.google_common import GoogleCloudAdapterBase, build_google_config_schema


class GoogleTaINNeural2DAdapter(GoogleCloudAdapterBase):
    model_id = "google:ta-IN-Neural2-D"
    display_name = "Google Cloud - ta-IN-Neural2-D"
    language_code = "ta-IN"
    voice_name = "ta-IN-Neural2-D"
    config_schema = build_google_config_schema(default_language_code=language_code, default_voice_name=voice_name)
