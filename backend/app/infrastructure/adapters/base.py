from __future__ import annotations

from typing import Any

import httpx

from app.domain.contracts import TTSAdapter
from app.domain.entities import ConfigStatus
from app.infrastructure.config.settings import Settings


class BaseAdapter(TTSAdapter):
    required_settings_fields: list[str] = []

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self.settings = settings
        self.http_client = http_client

    def check_configuration(self) -> ConfigStatus:
        warnings: list[str] = []
        for field in self.required_settings_fields:
            value = getattr(self.settings, field, None)
            if value is None or value == "":
                env_name = field.upper()
                warnings.append(f"Missing env: {env_name}")
        return ConfigStatus(configured=len(warnings) == 0, warnings=warnings)

    @staticmethod
    def _coerce_float(config: dict[str, Any], key: str, default: float) -> float:
        value = config.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _coerce_int(config: dict[str, Any], key: str, default: int) -> int:
        value = config.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
