from __future__ import annotations

from app.infrastructure.adapters.cloud.aws_polly_common import AWSPollyAdapterBase, build_aws_polly_config_schema


class AWSTaINRamyaAdapter(AWSPollyAdapterBase):
    model_id = "aws:ta-IN-RamyaNeural"
    display_name = "Amazon AWS - ta-IN-RamyaNeural"
    voice_id = "Ramya"
    language_code = "ta-IN"
    config_schema = build_aws_polly_config_schema(default_language_code=language_code, default_voice_id=voice_id)
