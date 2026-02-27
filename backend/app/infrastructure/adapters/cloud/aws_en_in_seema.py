from __future__ import annotations

from app.infrastructure.adapters.cloud.aws_polly_common import AWSPollyAdapterBase


class AWSEnINSeemaAdapter(AWSPollyAdapterBase):
    model_id = "aws:en-IN-SeemaNeural"
    display_name = "Amazon AWS - en-IN-SeemaNeural"
    voice_id = "Seema"
    language_code = "en-IN"
