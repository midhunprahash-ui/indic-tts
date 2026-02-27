from __future__ import annotations

from app.infrastructure.adapters.cloud.google_common import GoogleCloudAdapterBase


class GoogleEnINChirp3HDAdapter(GoogleCloudAdapterBase):
    model_id = "google:en-IN-Chirp3-HD"
    display_name = "Google Cloud - en-IN-Chirp3-HD"
    language_code = "en-IN"
    voice_name = "en-IN-Chirp3-HD"
