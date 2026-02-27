from __future__ import annotations

from typing import Any

from app.domain.entities import AdapterAudio
from app.infrastructure.adapters.base import BaseAdapter
from app.infrastructure.adapters.self_hosted.hf_runtime import HFLocalRuntime


class SelfHostedAdapterBase(BaseAdapter):
    provider = "huggingface-local"
    category = "self_hosted"

    def __init__(self, settings, http_client, runtime: HFLocalRuntime):
        super().__init__(settings, http_client)
        self.runtime = runtime

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        _ = prefer_streaming
        audio = await self.runtime.synthesize(self.model_id, text, config)
        return AdapterAudio(audio_bytes=audio, audio_format="wav", streaming_used=False)
