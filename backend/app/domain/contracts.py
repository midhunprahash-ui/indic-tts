from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.entities import AdapterAudio, ConfigField, ConfigStatus, ModelCapabilities, ModelCategory


class TTSAdapter(ABC):
    model_id: str
    display_name: str
    provider: str
    category: ModelCategory
    capabilities: ModelCapabilities
    config_schema: list[ConfigField]
    runtime_alias: str | None = None

    @abstractmethod
    def check_configuration(self) -> ConfigStatus:
        raise NotImplementedError

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        config: dict[str, Any],
        prefer_streaming: bool,
    ) -> AdapterAudio:
        raise NotImplementedError
