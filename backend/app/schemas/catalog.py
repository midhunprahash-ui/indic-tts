from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.entities import ModelCatalogItem


class ModelCatalogResponse(BaseModel):
    models: list[ModelCatalogItem] = Field(default_factory=list)
