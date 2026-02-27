from __future__ import annotations

from app.infrastructure.adapters.cloud.google_common import GoogleCloudAdapterBase


class GoogleTaINNeural2DAdapter(GoogleCloudAdapterBase):
    model_id = "google:ta-IN-Neural2-D"
    display_name = "Google Cloud - ta-IN-Neural2-D"
    language_code = "ta-IN"
    voice_name = "ta-IN-Neural2-D"
