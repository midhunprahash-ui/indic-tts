from __future__ import annotations

import tempfile
from typing import Any

import httpx
import pytest

from app.application.synthesis_service import SynthesisService
from app.domain.contracts import TTSAdapter
from app.domain.entities import AdapterAudio, ConfigStatus, ModelCapabilities
from app.domain.errors import ModelUnavailableError
from app.infrastructure.audio_store import AudioStore
from app.infrastructure.config.settings import Settings


class SuccessAdapter(TTSAdapter):
    model_id = "ok-model"
    display_name = "OK"
    provider = "test"
    category = "cloud"
    capabilities = ModelCapabilities()
    config_schema = []
    runtime_alias = None

    def check_configuration(self) -> ConfigStatus:
        return ConfigStatus(configured=True, warnings=[])

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        _ = (text, config, prefer_streaming)
        return AdapterAudio(audio_bytes=b"dummy-audio", audio_format="wav", streaming_used=False)


class FailingAdapter(TTSAdapter):
    model_id = "bad-model"
    display_name = "BAD"
    provider = "test"
    category = "cloud"
    capabilities = ModelCapabilities()
    config_schema = []
    runtime_alias = None

    def check_configuration(self) -> ConfigStatus:
        return ConfigStatus(configured=True, warnings=[])

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        _ = (text, config, prefer_streaming)
        raise ModelUnavailableError("upstream crashed")


@pytest.mark.asyncio
async def test_model_failure_isolation_in_batch() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Settings(audio_store_dir=tmpdir, public_audio_base_url="http://localhost:8000")
        service = SynthesisService(
            adapters={"ok-model": SuccessAdapter(), "bad-model": FailingAdapter()},
            settings=cfg,
            audio_store=AudioStore(cfg),
        )

        results = await service.synthesize_batch(
            model_ids=["ok-model", "bad-model"],
            text="hello",
            per_model_config={},
            prefer_streaming=True,
        )

        by_id = {r.model_id: r for r in results}
        assert by_id["ok-model"].success is True
        assert by_id["ok-model"].audio_url is not None
        assert by_id["bad-model"].success is False
        assert "upstream crashed" in (by_id["bad-model"].error or "")
