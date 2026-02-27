from __future__ import annotations

from functools import lru_cache

import httpx

from app.application.catalog_service import CatalogService
from app.application.synthesis_service import SynthesisService
from app.domain.contracts import TTSAdapter
from app.infrastructure.adapters.factory import build_adapters
from app.infrastructure.audio_store import AudioStore
from app.infrastructure.config.settings import Settings, settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return settings


@lru_cache(maxsize=1)
def get_http_client() -> httpx.AsyncClient:
    cfg = get_settings()
    return httpx.AsyncClient(timeout=cfg.request_timeout_seconds)


@lru_cache(maxsize=1)
def get_adapters() -> dict[str, TTSAdapter]:
    return build_adapters(settings=get_settings(), http_client=get_http_client())


@lru_cache(maxsize=1)
def get_audio_store() -> AudioStore:
    return AudioStore(settings=get_settings())


@lru_cache(maxsize=1)
def get_catalog_service() -> CatalogService:
    return CatalogService(get_adapters())


@lru_cache(maxsize=1)
def get_synthesis_service() -> SynthesisService:
    return SynthesisService(get_adapters(), settings=get_settings(), audio_store=get_audio_store())
