from __future__ import annotations

import asyncio
import tempfile
from typing import Any

import pytest

from app.application.synthesis_service import SynthesisService
from app.domain.contracts import TTSAdapter
from app.domain.entities import AdapterAudio, ConfigStatus, ModelCapabilities
from app.domain.errors import NotConfiguredError
from app.infrastructure.audio_store import AudioStore
from app.infrastructure.config.settings import Settings


class SlowAdapter(TTSAdapter):
    model_id = "slow-model"
    display_name = "SLOW"
    provider = "test"
    category = "cloud"
    capabilities = ModelCapabilities()
    config_schema = []
    runtime_alias = None

    def check_configuration(self) -> ConfigStatus:
        return ConfigStatus(configured=True, warnings=[])

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        _ = (text, config, prefer_streaming)
        await asyncio.sleep(2)
        return AdapterAudio(audio_bytes=b"slow-audio", audio_format="wav", streaming_used=False)


class NotConfiguredAdapter(TTSAdapter):
    model_id = "not-configured"
    display_name = "NC"
    provider = "test"
    category = "cloud"
    capabilities = ModelCapabilities()
    config_schema = []
    runtime_alias = None

    def check_configuration(self) -> ConfigStatus:
        return ConfigStatus(configured=False, warnings=["Missing env: TEST_KEY"])

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        _ = (text, config, prefer_streaming)
        raise NotConfiguredError("Missing env: TEST_KEY")


class FastAdapter(TTSAdapter):
    model_id = "fast-model"
    display_name = "FAST"
    provider = "test"
    category = "cloud"
    capabilities = ModelCapabilities()
    config_schema = []
    runtime_alias = None

    def check_configuration(self) -> ConfigStatus:
        return ConfigStatus(configured=True, warnings=[])

    async def synthesize(self, text: str, config: dict[str, Any], prefer_streaming: bool) -> AdapterAudio:
        _ = (text, config, prefer_streaming)
        return AdapterAudio(audio_bytes=b"ok", audio_format="wav", streaming_used=False)


@pytest.mark.asyncio
async def test_partial_success_with_timeout_and_not_configured() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Settings(
            audio_store_dir=tmpdir,
            public_audio_base_url="http://localhost:8000",
            model_timeout_seconds=1,
        )
        service = SynthesisService(
            adapters={
                "slow-model": SlowAdapter(),
                "not-configured": NotConfiguredAdapter(),
                "fast-model": FastAdapter(),
            },
            settings=cfg,
            audio_store=AudioStore(cfg),
        )

        results = await service.synthesize_batch(
            model_ids=["slow-model", "not-configured", "fast-model"],
            text="hi",
            per_model_config={},
            prefer_streaming=True,
        )

        by_id = {r.model_id: r for r in results}
        assert by_id["fast-model"].success is True
        assert by_id["slow-model"].success is False
        assert "Timed out" in (by_id["slow-model"].error or "")
        assert by_id["not-configured"].success is False
        assert "Missing env" in (by_id["not-configured"].error or "")
