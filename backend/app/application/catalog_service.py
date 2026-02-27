from __future__ import annotations

from app.domain.entities import ModelCatalogItem
from app.domain.contracts import TTSAdapter


class CatalogService:
    def __init__(self, adapters: dict[str, TTSAdapter]):
        self._adapters = adapters

    def get_catalog(self) -> list[ModelCatalogItem]:
        items: list[ModelCatalogItem] = []
        for adapter in self._adapters.values():
            status = adapter.check_configuration()
            items.append(
                ModelCatalogItem(
                    model_id=adapter.model_id,
                    display_name=adapter.display_name,
                    provider=adapter.provider,
                    category=adapter.category,
                    capabilities=adapter.capabilities,
                    config_schema=adapter.config_schema,
                    configured=status.configured,
                    config_warnings=status.warnings,
                    runtime_alias=adapter.runtime_alias,
                )
            )
        return items
