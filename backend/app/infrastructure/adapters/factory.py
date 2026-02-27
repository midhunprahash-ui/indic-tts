from __future__ import annotations

import httpx

from app.domain.contracts import TTSAdapter
from app.infrastructure.adapters.cloud.aws_en_in_seema import AWSEnINSeemaAdapter
from app.infrastructure.adapters.cloud.aws_ta_in_ramya import AWSTaINRamyaAdapter
from app.infrastructure.adapters.cloud.azure_en_neerja import AzureEnINNeerjaAdapter
from app.infrastructure.adapters.cloud.azure_ta_sweta import AzureTaINSwetaAdapter
from app.infrastructure.adapters.cloud.elevenlabs_adam_indian import ElevenLabsAdamIndianAdapter
from app.infrastructure.adapters.cloud.google_chirp3_hd import GoogleEnINChirp3HDAdapter
from app.infrastructure.adapters.cloud.google_ta_neural2_d import GoogleTaINNeural2DAdapter
from app.infrastructure.adapters.cloud.sarvam_bulbul_v2 import SarvamBulbulV2Adapter
from app.infrastructure.adapters.cloud.sarvam_bulbul_v3_beta import SarvamBulbulV3BetaAdapter
from app.infrastructure.adapters.remote.indic_parler import RemoteIndicParlerAdapter
from app.infrastructure.adapters.remote.veena_all_v1 import RemoteVeenaAllV1Adapter
from app.infrastructure.adapters.self_hosted.hf_runtime import HFLocalRuntime
from app.infrastructure.adapters.self_hosted.indic_parler import IndicParlerAdapter
from app.infrastructure.adapters.self_hosted.veena_all_v1 import VeenaAllV1Adapter
from app.infrastructure.config.settings import Settings


def _build_cloud_adapters(settings: Settings, http_client: httpx.AsyncClient) -> list[TTSAdapter]:
    return [
        SarvamBulbulV3BetaAdapter(settings, http_client),
        SarvamBulbulV2Adapter(settings, http_client),
        GoogleEnINChirp3HDAdapter(settings, http_client),
        GoogleTaINNeural2DAdapter(settings, http_client),
        AzureTaINSwetaAdapter(settings, http_client),
        AzureEnINNeerjaAdapter(settings, http_client),
        AWSEnINSeemaAdapter(settings, http_client),
        AWSTaINRamyaAdapter(settings, http_client),
        ElevenLabsAdamIndianAdapter(settings, http_client),
    ]


def _build_local_self_hosted_adapters(settings: Settings, http_client: httpx.AsyncClient) -> list[TTSAdapter]:
    runtime = HFLocalRuntime(settings)
    adapters: list[TTSAdapter] = [
        IndicParlerAdapter(settings, http_client, runtime),
        VeenaAllV1Adapter(settings, http_client, runtime),
    ]
    for adapter in adapters:
        if adapter.model_id == "maya-research/veena-all-v1":
            adapter.runtime_alias = settings.hf_alias_maya_research_veena_all_v1
    return adapters


def _build_remote_self_hosted_adapters(settings: Settings, http_client: httpx.AsyncClient) -> list[TTSAdapter]:
    return [
        RemoteIndicParlerAdapter(settings, http_client),
        RemoteVeenaAllV1Adapter(settings, http_client),
    ]


def build_adapters(settings: Settings, http_client: httpx.AsyncClient) -> dict[str, TTSAdapter]:
    role = (settings.backend_role or "all_local").strip().lower()

    if role == "self_hosted_worker":
        adapters = _build_local_self_hosted_adapters(settings=settings, http_client=http_client)
    elif role == "orchestrator":
        adapters = [
            *_build_cloud_adapters(settings=settings, http_client=http_client),
            *_build_remote_self_hosted_adapters(settings=settings, http_client=http_client),
        ]
    else:
        adapters = [
            *_build_cloud_adapters(settings=settings, http_client=http_client),
            *_build_local_self_hosted_adapters(settings=settings, http_client=http_client),
        ]
    return {adapter.model_id: adapter for adapter in adapters}
