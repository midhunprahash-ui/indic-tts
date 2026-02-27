from __future__ import annotations

import asyncio
import base64

import httpx
import pytest

from app.infrastructure.adapters.factory import build_adapters
from app.infrastructure.adapters.remote.indic_parler import RemoteIndicParlerAdapter
from app.infrastructure.config.settings import Settings


def test_orchestrator_role_uses_remote_self_hosted_adapters() -> None:
    settings = Settings(
        backend_role="orchestrator",
        remote_self_hosted_url="https://worker.example",
    )
    http_client = httpx.AsyncClient()
    adapters = build_adapters(settings=settings, http_client=http_client)

    assert "sarvam:bulbul:v2" in adapters
    assert "ai4bharat/indic-parler-tts" in adapters
    assert "maya-research/veena-all-v1" in adapters
    assert adapters["ai4bharat/indic-parler-tts"].provider == "lightning-ai"
    assert adapters["maya-research/veena-all-v1"].provider == "lightning-ai"
    asyncio.run(http_client.aclose())


def test_self_hosted_worker_role_exposes_only_local_self_hosted_models() -> None:
    settings = Settings(backend_role="self_hosted_worker")
    http_client = httpx.AsyncClient()
    adapters = build_adapters(settings=settings, http_client=http_client)

    assert set(adapters.keys()) == {
        "ai4bharat/indic-parler-tts",
        "maya-research/veena-all-v1",
    }
    assert adapters["ai4bharat/indic-parler-tts"].provider == "huggingface-local"
    assert adapters["maya-research/veena-all-v1"].provider == "huggingface-local"
    asyncio.run(http_client.aclose())


def test_remote_adapter_requires_remote_url() -> None:
    settings = Settings(backend_role="orchestrator", remote_self_hosted_url=None)
    http_client = httpx.AsyncClient()
    adapter = RemoteIndicParlerAdapter(settings=settings, http_client=http_client)
    status = adapter.check_configuration()
    assert status.configured is False
    assert any("REMOTE_SELF_HOSTED_URL" in warning for warning in status.warnings)
    asyncio.run(http_client.aclose())


@pytest.mark.asyncio
async def test_remote_adapter_decodes_audio_payload() -> None:
    audio = b"remote-audio"
    encoded = base64.b64encode(audio).decode("utf-8")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/tts/synthesize"
        return httpx.Response(
            200,
            json={
                "result": {
                    "model_id": "ai4bharat/indic-parler-tts",
                    "success": True,
                    "audio_base64": encoded,
                    "audio_url": None,
                    "latency_ms": 123,
                    "streaming_used": False,
                    "error": None,
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        backend_role="orchestrator",
        remote_self_hosted_url="https://worker.example",
        remote_self_hosted_timeout_seconds=30,
    )
    adapter = RemoteIndicParlerAdapter(settings=settings, http_client=client)
    result = await adapter.synthesize(text="hello", config={}, prefer_streaming=True)
    await client.aclose()

    assert result.audio_bytes == audio
    assert result.audio_format == "wav"
    assert result.streaming_used is False
