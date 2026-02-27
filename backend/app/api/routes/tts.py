from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter

from app.api.deps import get_audio_store, get_synthesis_service
from app.schemas.common import SummaryEnvelope
from app.schemas.tts import BatchSynthesizeRequest, BatchSynthesizeResponse, SynthesizeRequest, SynthesizeResponse

router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(request: SynthesizeRequest) -> SynthesizeResponse:
    result = await get_synthesis_service().synthesize_one(
        model_id=request.model_id,
        text=request.text,
        config_overrides=request.config_overrides,
        prefer_streaming=request.prefer_streaming,
    )
    return SynthesizeResponse(result=result)


@router.post("/synthesize-batch", response_model=BatchSynthesizeResponse)
async def synthesize_batch(request: BatchSynthesizeRequest) -> BatchSynthesizeResponse:
    started = perf_counter()
    results = await get_synthesis_service().synthesize_batch(
        model_ids=request.model_ids,
        text=request.text,
        per_model_config=request.per_model_config,
        prefer_streaming=request.prefer_streaming,
    )
    duration_ms = int((perf_counter() - started) * 1000)
    success_count = sum(1 for item in results if item.success)
    summary = SummaryEnvelope(
        total=len(results),
        success_count=success_count,
        failure_count=len(results) - success_count,
        duration_ms=duration_ms,
    )
    return BatchSynthesizeResponse(results=results, summary=summary)


@router.get("/audio/{audio_id}")
async def serve_audio(audio_id: str):
    return get_audio_store().serve(audio_id)
