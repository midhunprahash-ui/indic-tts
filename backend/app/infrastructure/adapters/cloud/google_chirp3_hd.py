from __future__ import annotations

from app.infrastructure.adapters.cloud.google_common import GoogleCloudAdapterBase, build_google_config_schema


class GoogleEnINChirp3HDAdapter(GoogleCloudAdapterBase):
    model_id = "google:en-IN-Chirp3-HD"
    display_name = "Google Cloud - en-IN-Chirp3-HD"
    language_code = "en-IN"
    voice_name = "en-IN-Chirp3-HD"
    config_schema = build_google_config_schema(default_language_code=language_code, default_voice_name=voice_name)
