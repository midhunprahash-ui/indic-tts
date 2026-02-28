from __future__ import annotations

from app.infrastructure.adapters.cloud.aws_polly_common import AWSPollyAdapterBase, build_aws_polly_config_schema


class AWSEnINSeemaAdapter(AWSPollyAdapterBase):
    model_id = "aws:en-IN-SeemaNeural"
    display_name = "Amazon AWS - en-IN-SeemaNeural"
    voice_id = "Seema"
    language_code = "en-IN"
    config_schema = build_aws_polly_config_schema(default_language_code=language_code, default_voice_id=voice_id)
