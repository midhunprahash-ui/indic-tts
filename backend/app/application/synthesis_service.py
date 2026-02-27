from __future__ import annotations

import asyncio
import base64
from time import perf_counter
from typing import Any

from app.application.timeout import run_with_timeout
from app.domain.contracts import TTSAdapter
from app.domain.entities import SynthesisResult
from app.domain.errors import AdapterError, DependencyMissingError, NotConfiguredError
from app.infrastructure.audio_store import AudioStore
from app.infrastructure.config.settings import Settings


class SynthesisService:
    def __init__(self, adapters: dict[str, TTSAdapter], settings: Settings, audio_store: AudioStore):
        self._adapters = adapters
        self._settings = settings
        self._audio_store = audio_store
        self._sem = asyncio.Semaphore(settings.max_concurrent_synth)

    async def synthesize_one(
        self,
        model_id: str,
        text: str,
        config_overrides: dict[str, Any],
        prefer_streaming: bool,
    ) -> SynthesisResult:
        adapter = self._adapters.get(model_id)
        if not adapter:
            return self._failed_result(model_id, 0, "Unknown model_id")

        async with self._sem:
            started = perf_counter()
            try:
                status = adapter.check_configuration()
                if not status.configured:
                    raise NotConfiguredError("; ".join(status.warnings) or "Model is not configured")

                timeout_seconds = self._settings.model_timeout_seconds
                if getattr(adapter, "category", "") == "self_hosted":
                    timeout_seconds = max(timeout_seconds, self._settings.local_model_timeout_seconds)

                audio = await run_with_timeout(
                    adapter.synthesize(text=text, config=config_overrides, prefer_streaming=prefer_streaming),
                    timeout_seconds=timeout_seconds,
                )
                latency = int((perf_counter() - started) * 1000)
                audio_id = self._audio_store.save(audio.audio_bytes, audio.audio_format)
                return SynthesisResult(
                    model_id=model_id,
                    success=True,
                    audio_base64=base64.b64encode(audio.audio_bytes).decode("utf-8"),
                    audio_url=self._audio_store.to_url(audio_id),
                    latency_ms=latency,
                    streaming_used=audio.streaming_used,
                    error=None,
                )
            except (NotConfiguredError, DependencyMissingError, AdapterError) as exc:
                latency = int((perf_counter() - started) * 1000)
                return self._failed_result(model_id=model_id, latency_ms=latency, error=str(exc))
            except Exception as exc:  # noqa: BLE001
                latency = int((perf_counter() - started) * 1000)
                return self._failed_result(model_id=model_id, latency_ms=latency, error=f"Unhandled adapter error: {exc}")

    async def synthesize_batch(
        self,
        model_ids: list[str],
        text: str,
        per_model_config: dict[str, dict[str, Any]],
        prefer_streaming: bool,
    ) -> list[SynthesisResult]:
        tasks = [
            asyncio.create_task(
                self.synthesize_one(
                    model_id=model_id,
                    text=text,
                    config_overrides=per_model_config.get(model_id, {}),
                    prefer_streaming=prefer_streaming,
                )
            )
            for model_id in model_ids
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    @staticmethod
    def _failed_result(model_id: str, latency_ms: int, error: str) -> SynthesisResult:
        return SynthesisResult(
            model_id=model_id,
            success=False,
            audio_base64=None,
            audio_url=None,
            latency_ms=latency_ms,
            streaming_used=False,
            error=error,
        )
