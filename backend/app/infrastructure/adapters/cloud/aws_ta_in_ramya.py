from __future__ import annotations

from app.infrastructure.adapters.cloud.aws_polly_common import AWSPollyAdapterBase


class AWSTaINRamyaAdapter(AWSPollyAdapterBase):
    model_id = "aws:ta-IN-RamyaNeural"
    display_name = "Amazon AWS - ta-IN-RamyaNeural"
    voice_id = "Ramya"
    language_code = "ta-IN"
