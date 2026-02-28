from __future__ import annotations

import asyncio
import io
import wave
from collections import defaultdict
from typing import Any

from app.domain.errors import DependencyMissingError, ModelUnavailableError
from app.infrastructure.config.settings import Settings


class HFLocalRuntime:
    _VEENA_SPEAKERS = {"kavya", "agastya", "maitri", "vinaya"}

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

        if "maya-research/veena" in model_repo.lower():
            return self._load_veena_runtime(model_repo=model_repo, device_pref=device_pref, torch_module=torch)

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
        if isinstance(model_pipeline, dict) and model_pipeline.get("kind") == "veena":
            return self._run_veena(model_pipeline, text, config)

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
        prompt_tokenizer = AutoTokenizer.from_pretrained(
            model_repo,
            token=self._settings.hf_token if self._settings.hf_token else None,
        )
        text_encoder = getattr(model.config, "text_encoder", None)
        description_tokenizer_id = getattr(text_encoder, "_name_or_path", None) or model_repo
        description_tokenizer = AutoTokenizer.from_pretrained(
            description_tokenizer_id,
            token=self._settings.hf_token if self._settings.hf_token else None,
        )
        return {
            "kind": "parler",
            "model": model,
            "prompt_tokenizer": prompt_tokenizer,
            "description_tokenizer": description_tokenizer,
            "device": device,
        }

    def _load_veena_runtime(self, model_repo: str, device_pref: str, torch_module):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise DependencyMissingError("transformers is required for Veena runtime") from exc
        try:
            from snac import SNAC
        except ImportError as exc:
            raise DependencyMissingError("snac is required for Veena runtime. Install with `pip install snac`.") from exc

        token_kwargs: dict[str, Any] = {}
        if self._settings.hf_token:
            token_kwargs["token"] = self._settings.hf_token

        use_cuda = device_pref.startswith("cuda") and torch_module.cuda.is_available()
        model_kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "torch_dtype": torch_module.float16 if use_cuda else torch_module.float32,
        }

        try:
            model = AutoModelForCausalLM.from_pretrained(model_repo, **token_kwargs, **model_kwargs)
            if use_cuda:
                model = model.to("cuda:0")
            model = model.eval()
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"Failed to load Veena model '{model_repo}': {exc}") from exc

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_repo, trust_remote_code=True, **token_kwargs)
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"Failed to load Veena tokenizer '{model_repo}': {exc}") from exc

        try:
            snac_model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz")
            if use_cuda:
                snac_model = snac_model.eval().cuda()
            else:
                snac_model = snac_model.eval()
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"Failed to load SNAC decoder for Veena: {exc}") from exc

        return {"kind": "veena", "model": model, "tokenizer": tokenizer, "snac_model": snac_model}

    def _run_parler(self, runtime: dict[str, Any], text: str, config: dict[str, Any]) -> bytes:
        try:
            import torch
        except ImportError as exc:
            raise DependencyMissingError("torch is required for Parler runtime") from exc

        model = runtime["model"]
        prompt_tokenizer = runtime.get("prompt_tokenizer") or runtime.get("tokenizer")
        description_tokenizer = runtime.get("description_tokenizer") or prompt_tokenizer
        if prompt_tokenizer is None or description_tokenizer is None:
            raise ModelUnavailableError("Indic Parler runtime tokenizers are not initialized")
        device = runtime["device"]
        base_description = str(
            config.get("description")
            or "Jaya speaks Tamil with clear pronunciation, moderate pace, and very clear audio."
        ).strip()
        # `text` is always the utterance from the main input field.
        # Optional prompt field is treated as style guidance, not replacement transcript.
        style_hint = str(config.get("prompt") or "").strip()
        description = f"{base_description.rstrip('. ')}. {style_hint}" if style_hint else base_description
        prompt_text = str(text)

        description_inputs = description_tokenizer(description, return_tensors="pt")
        prompt_inputs = prompt_tokenizer(prompt_text, return_tensors="pt")
        input_ids = description_inputs.input_ids.to(device)
        attention_mask = description_inputs.attention_mask.to(device)
        prompt_input_ids = prompt_inputs.input_ids.to(device)
        prompt_attention_mask = prompt_inputs.attention_mask.to(device)

        try:
            with torch.no_grad():
                generation = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    prompt_input_ids=prompt_input_ids,
                    prompt_attention_mask=prompt_attention_mask,
                )
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"Parler generation failed: {exc}") from exc

        audio_arr = generation.cpu().numpy().squeeze()
        sample_rate = int(getattr(model.config, "sampling_rate", 24000))
        return self._array_to_wav_bytes(audio_arr, sample_rate)

    def _run_veena(self, runtime: dict[str, Any], text: str, config: dict[str, Any]) -> bytes:
        try:
            import torch
        except ImportError as exc:
            raise DependencyMissingError("torch is required for Veena runtime") from exc

        model = runtime["model"]
        tokenizer = runtime["tokenizer"]
        snac_model = runtime["snac_model"]

        speaker = str(config.get("speaker") or "kavya").strip().lower()
        if speaker not in self._VEENA_SPEAKERS:
            speaker = "kavya"

        # Model-card constants for Veena audio-token decoding.
        start_of_speech = 128257
        end_of_speech = 128258
        start_of_human = 128259
        end_of_human = 128260
        start_of_ai = 128261
        end_of_ai = 128262
        audio_code_base_offset = 128266
        llm_codebook_offsets = [audio_code_base_offset + i * 4096 for i in range(7)]

        style_prompt = str(config.get("prompt") or "").strip()
        veena_text = f"{style_prompt}. {text}" if style_prompt else text
        prompt = f"<spk_{speaker}> {veena_text}"
        prompt_tokens = tokenizer.encode(prompt, add_special_tokens=False)
        input_tokens = [start_of_human, *prompt_tokens, end_of_human, start_of_ai, start_of_speech]

        max_new_tokens = self._bounded_max_new_tokens(config=config, text=veena_text)
        if "max_new_tokens" not in config:
            inferred = min(max(int(len(veena_text) * 1.3) * 7 + 21, 128), 700)
            max_new_tokens = max(max_new_tokens, inferred)

        try:
            model_device = next(model.parameters()).device
        except Exception:  # noqa: BLE001
            model_device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        temperature = self._coerce_optional_float(config.get("temperature"), 0.4)
        top_p = self._coerce_optional_float(config.get("top_p"), 0.9)
        min_new_tokens = max(128, min(512, max_new_tokens // 3))

        input_ids = torch.tensor([input_tokens], device=model_device)
        try:
            with torch.no_grad():
                output = model.generate(
                    input_ids,
                    min_new_tokens=min_new_tokens,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=temperature,
                    top_p=top_p,
                    repetition_penalty=1.05,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                )
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"Veena generation failed: {exc}") from exc

        generated_ids = output[0][len(input_tokens) :].tolist()
        snac_tokens = [
            token_id
            for token_id in generated_ids
            if audio_code_base_offset <= token_id < (audio_code_base_offset + 7 * 4096)
        ]
        if not snac_tokens:
            raise ModelUnavailableError("Veena generated no audio tokens")

        remainder = len(snac_tokens) % 7
        if remainder:
            snac_tokens = snac_tokens[: len(snac_tokens) - remainder]
        if not snac_tokens:
            raise ModelUnavailableError("Veena generated invalid audio-token sequence")

        codes_lvl = [[], [], []]
        for i in range(0, len(snac_tokens), 7):
            codes_lvl[0].append(snac_tokens[i] - llm_codebook_offsets[0])
            codes_lvl[1].append(snac_tokens[i + 1] - llm_codebook_offsets[1])
            codes_lvl[1].append(snac_tokens[i + 4] - llm_codebook_offsets[4])
            codes_lvl[2].append(snac_tokens[i + 2] - llm_codebook_offsets[2])
            codes_lvl[2].append(snac_tokens[i + 3] - llm_codebook_offsets[3])
            codes_lvl[2].append(snac_tokens[i + 5] - llm_codebook_offsets[5])
            codes_lvl[2].append(snac_tokens[i + 6] - llm_codebook_offsets[6])

        try:
            snac_device = next(snac_model.parameters()).device
        except Exception:  # noqa: BLE001
            snac_device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        hierarchical_codes = []
        for lvl_codes in codes_lvl:
            tensor = torch.tensor(lvl_codes, dtype=torch.int32, device=snac_device).unsqueeze(0)
            if torch.any((tensor < 0) | (tensor > 4095)):
                raise ModelUnavailableError("Veena produced out-of-range SNAC tokens")
            hierarchical_codes.append(tensor)

        try:
            with torch.no_grad():
                audio_hat = snac_model.decode(hierarchical_codes)
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(f"SNAC decode failed for Veena: {exc}") from exc

        audio_arr = audio_hat.squeeze().clamp(-1, 1).cpu().numpy()
        return self._array_to_wav_bytes(audio_arr, 24000)

    @staticmethod
    def _coerce_optional_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

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
            raw_sample_rate = result.get("sampling_rate")
            if raw_sample_rate is not None:
                try:
                    sample_rate = int(raw_sample_rate)
                except (TypeError, ValueError):
                    pass
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
        if arr.size == 0:
            raise ModelUnavailableError("Local model produced empty audio array")

        channels = 1
        if arr.ndim == 1:
            pass
        elif arr.ndim == 2:
            # Normalize to shape (frames, channels).
            if arr.shape[0] <= 8 and arr.shape[1] > arr.shape[0]:
                arr = arr.T
            channels = int(arr.shape[1])
            if channels <= 0:
                raise ModelUnavailableError("Local model produced invalid channel dimension")
        else:
            arr = np.squeeze(arr)
            if arr.ndim > 2:
                arr = arr.reshape(-1)
            if arr.ndim == 2:
                if arr.shape[0] <= 8 and arr.shape[1] > arr.shape[0]:
                    arr = arr.T
                channels = int(arr.shape[1])

        if arr.dtype.kind == "f":
            arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
            max_abs = float(np.max(np.abs(arr)))
            if max_abs > 1.0:
                arr = arr / max_abs
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767).astype(np.int16)
        elif arr.dtype != np.int16:
            arr = np.clip(arr, -32768, 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(arr.tobytes())
        return buffer.getvalue()
