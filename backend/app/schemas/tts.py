from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.entities import SynthesisResult
from app.schemas.common import SummaryEnvelope


class SynthesizeRequest(BaseModel):
    model_id: str
    text: str = Field(min_length=1, max_length=5000)
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    prefer_streaming: bool = True


class BatchSynthesizeRequest(BaseModel):
    model_ids: list[str] = Field(min_length=1)
    text: str = Field(min_length=1, max_length=5000)
    per_model_config: dict[str, dict[str, Any]] = Field(default_factory=dict)
    prefer_streaming: bool = True


class SynthesizeResponse(BaseModel):
    result: SynthesisResult


class BatchSynthesizeResponse(BaseModel):
    results: list[SynthesisResult]
    summary: SummaryEnvelope
