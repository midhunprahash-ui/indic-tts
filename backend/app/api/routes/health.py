from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import get_adapters
from app.schemas.common import AppWarning, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    warnings: list[AppWarning] = []
    for adapter in get_adapters().values():
        status = adapter.check_configuration()
        for warning in status.warnings:
            warnings.append(AppWarning(model_id=adapter.model_id, warning=warning))
    return HealthResponse(status="ok", warnings=warnings)
