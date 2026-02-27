from __future__ import annotations

import asyncio
import io
import wave
from collections import defaultdict
from typing import Any

from app.domain.errors import DependencyMissingError, ModelUnavailableError
from app.infrastructure.config.settings import Settings


class HFLocalRuntime:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._pipelines: dict[str, Any] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def resolve_model_repo(self, requested_id: str) -> str:
        aliases = {
            "maya-research/veena-all-v1": self._settings.hf_alias_maya_research_veena_all_v1,
        }
        return aliases.get(requested_id, requested_id)

    async def synthesize(self, requested_id: str, text: str, config: dict[str, Any]) -> bytes:
        model_repo = self.resolve_model_repo(requested_id)
        pipeline = await self._get_or_load_pipeline(model_repo)
        return await asyncio.to_thread(self._run_pipeline, pipeline, text, config)

    async def _get_or_load_pipeline(self, model_repo: str):
        if model_repo in self._pipelines:
            return self._pipelines[model_repo]

        async with self._locks[model_repo]:
            if model_repo in self._pipelines:
                return self._pipelines[model_repo]
            loaded = await asyncio.to_thread(self._load_pipeline_sync, model_repo)
            self._pipelines[model_repo] = loaded
            return loaded

    def _load_pipeline_sync(self, model_repo: str):
        try:
            import torch
            from transformers import pipeline
        except ImportError as exc:
            raise DependencyMissingError(
                "Self-hosted inference dependencies missing. Install transformers, torch, and numpy."
            ) from exc

        device_pref = (self._settings.local_device or "cpu").lower()
        device = -1
        if device_pref.startswith("cuda") and torch.cuda.is_available():
            device = 0

        if "indic-parler-tts" in model_repo.lower():
            return self._load_parler_runtime(model_repo=model_repo, device_pref=device_pref, torch_module=torch)

        if "parler" in model_repo.lower():
            try:
                import parler_tts  # noqa: F401
            except ImportError as exc:
                raise DependencyMissingError(
                    "parler-tts is required for indic-parler-tts. Install with `pip install parler-tts`."
                ) from exc

        kwargs: dict[str, Any] = {"model": model_repo, "device": device, "trust_remote_code": True}
        if self._settings.hf_token:
            kwargs["token"] = self._settings.hf_token

        errors: list[str] = []
        for task in ("text-to-speech", "text-to-audio"):
            try:
                return {"kind": "pipeline", "runner": pipeline(task=task, **kwargs)}
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{task}: {exc}")

        raise ModelUnavailableError(
            f"Failed to load local model '{model_repo}'. Model might require a custom runtime or gated access: {' | '.join(errors)}"
        )

    def _run_pipeline(self, model_pipeline: Any, text: str, config: dict[str, Any]) -> bytes:
        if isinstance(model_pipeline, dict) and model_pipeline.get("kind") == "parler":
            return self._run_parler(model_pipeline, text, config)

        runner = model_pipeline.get("runner") if isinstance(model_pipeline, dict) else model_pipeline
        kwargs: dict[str, Any] = {}
        if description := config.get("description"):
            kwargs["description"] = description
        if prompt := config.get("prompt"):
            kwargs["prompt"] = prompt

        try:
            result = runner(text, **kwargs)
        except TypeError as exc:
            # Some TTS pipelines accept only plain text with no style kwargs.
            if kwargs and "unexpected keyword argument" in str(exc):
                result = self._run_with_length_retry(runner=runner, text=text, kwargs={}, config=config)
            else:
                raise ModelUnavailableError(f"Local model inference failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            if self._is_max_length_error(exc):
                result = self._run_with_length_retry(runner=runner, text=text, kwargs=kwargs, config=config)
            else:
                raise ModelUnavailableError(f"Local model inference failed: {exc}") from exc

        return self._extract_audio_bytes(result)

    def _run_with_length_retry(
        self,
        runner: Any,
        text: str,
        kwargs: dict[str, Any],
        config: dict[str, Any],
    ) -> Any:
        try:
            return runner(text, **kwargs)
        except Exception as exc:  # noqa: BLE001
            if not self._is_max_length_error(exc):
                raise ModelUnavailableError(f"Local model inference failed: {exc}") from exc

        max_new_tokens = self._bounded_max_new_tokens(config=config, text=text)
        max_length = self._infer_max_length_from_error(config=config, text=text)

        attempts: list[dict[str, Any]] = [
            {**kwargs, "max_new_tokens": max_new_tokens},
            {**kwargs, "generate_kwargs": {"max_new_tokens": max_new_tokens}},
            {"max_new_tokens": max_new_tokens},
            {"generate_kwargs": {"max_new_tokens": max_new_tokens}},
            {**kwargs, "max_length": max_length},
            {"max_length": max_length},
        ]

        last_error: Exception | None = None
        for attempt_kwargs in attempts:
            try:
                return runner(text, **attempt_kwargs)
            except TypeError as exc:
                # Some pipeline wrappers reject specific generation kwargs.
                if "unexpected keyword argument" in str(exc):
                    last_error = exc
                    continue
                last_error = exc
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if self._is_max_length_error(exc):
                    continue
                break

        if last_error is None:
            raise ModelUnavailableError("Local model inference failed due to generation length settings.")
        raise ModelUnavailableError(f"Local model inference failed: {last_error}") from last_error

    @staticmethod
    def _is_max_length_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "input length of input_ids" in message and "max_length" in message

    @staticmethod
    def _bounded_max_new_tokens(config: dict[str, Any], text: str) -> int:
        fallback = max(128, min(1024, len(text.split()) * 8))
        raw = config.get("max_new_tokens", fallback)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = fallback
        return max(64, min(2048, value))

    def _infer_max_length_from_error(self, config: dict[str, Any], text: str) -> int:
        if raw_value := config.get("max_length"):
            try:
                parsed = int(raw_value)
                if parsed > 0:
                    return parsed
            except (TypeError, ValueError):
                pass

        estimated_input_len = max(64, len(text.split()) * 2)
        return estimated_input_len + self._bounded_max_new_tokens(config=config, text=text)

    def _load_parler_runtime(self, model_repo: str, device_pref: str, torch_module):
        try:
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise DependencyMissingError(
                "parler-tts runtime is missing. Install `parler-tts` and compatible transformers."
            ) from exc

        torch_dtype = getattr(torch_module, self._settings.local_dtype, torch_module.float32)
        device = "cuda:0" if device_pref.startswith("cuda") and torch_module.cuda.is_available() else "cpu"

        kwargs: dict[str, Any] = {"torch_dtype": torch_dtype}
        if self._settings.hf_token:
            kwargs["token"] = self._settings.hf_token

        model = ParlerTTSForConditionalGeneration.from_pretrained(model_repo, **kwargs)
        model = model.to(device)
        tokenizer = AutoTokenizer.from_pretrained(
            model_repo,
            token=self._settings.hf_token if self._settings.hf_token else None,
        )
        return {"kind": "parler", "model": model, "tokenizer": tokenizer, "device": device}

    def _run_parler(self, runtime: dict[str, Any], text: str, config: dict[str, Any]) -> bytes:
        try:
            import torch
        except ImportError as exc:
            raise DependencyMissingError("torch is required for Parler runtime") from exc

        model = runtime["model"]
        tokenizer = runtime["tokenizer"]
        device = runtime["device"]
        description = str(
            config.get("description")
            or "A warm Tanglish conversational voice with clear Tamil pronunciation and clean pacing."
        )
        prompt_text = str(config.get("prompt") or text)

        description_inputs = tokenizer(description, return_tensors="pt")
        prompt_inputs = tokenizer(prompt_text, return_tensors="pt")
        input_ids = description_inputs.input_ids.to(device)
        prompt_input_ids = prompt_inputs.input_ids.to(device)

        try:
            with torch.no_grad():
                generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_input_ids)
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"Parler generation failed: {exc}") from exc

        audio_arr = generation.cpu().numpy().squeeze()
        sample_rate = int(getattr(model.config, "sampling_rate", 24000))
        return self._array_to_wav_bytes(audio_arr, sample_rate)

    def _extract_audio_bytes(self, result: Any) -> bytes:
        audio_candidate = None
        sample_rate = 22050

        if isinstance(result, dict):
            if isinstance(result.get("audio"), (bytes, bytearray)):
                return bytes(result["audio"])
            for key in ("audio", "wav", "speech"):
                if key in result and result.get(key) is not None:
                    audio_candidate = result.get(key)
                    break
            sample_rate = int(result.get("sampling_rate", sample_rate))
        elif isinstance(result, (bytes, bytearray)):
            return bytes(result)
        else:
            audio_candidate = result

        if audio_candidate is None:
            raise ModelUnavailableError("Local model returned no audio payload")
        return self._array_to_wav_bytes(audio_candidate, sample_rate)

    @staticmethod
    def _array_to_wav_bytes(audio: Any, sample_rate: int) -> bytes:
        try:
            import numpy as np
        except ImportError as exc:
            raise DependencyMissingError("numpy is required to convert local model output to WAV") from exc

        arr = np.asarray(audio)
        if arr.ndim > 1:
            arr = arr.squeeze()
        if arr.size == 0:
            raise ModelUnavailableError("Local model produced empty audio array")

        if arr.dtype.kind == "f":
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767).astype(np.int16)
        elif arr.dtype != np.int16:
            arr = arr.astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(arr.tobytes())
        return buffer.getvalue()
