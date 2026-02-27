from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorEnvelope(BaseModel):
    detail: str


class SummaryEnvelope(BaseModel):
    total: int
    success_count: int
    failure_count: int
    duration_ms: int


class AppWarning(BaseModel):
    model_id: str
    warning: str


class HealthResponse(BaseModel):
    status: str = "ok"
    warnings: list[AppWarning] = Field(default_factory=list)
