from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import get_catalog_service
from app.schemas.catalog import ModelCatalogResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/catalog", response_model=ModelCatalogResponse)
async def get_catalog() -> ModelCatalogResponse:
    return ModelCatalogResponse(models=get_catalog_service().get_catalog())
