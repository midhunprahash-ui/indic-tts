from __future__ import annotations

from app.infrastructure.adapters.self_hosted.hf_runtime import HFLocalRuntime
from app.infrastructure.config.settings import Settings


class LengthLimitedRunner:
    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, text: str, **kwargs):
        _ = text
        self.calls.append(kwargs)
        max_new = kwargs.get("max_new_tokens")
        generate_kwargs = kwargs.get("generate_kwargs", {})
        max_length = kwargs.get("max_length")
        if max_new or generate_kwargs.get("max_new_tokens") or max_length:
            return b"\x00\x01\x02"
        raise ValueError(
            "Input length of input_ids is 105, but `max_length` is set to 20. "
            "This can lead to unexpected behavior."
        )


class PromptRejectingLengthRunner(LengthLimitedRunner):
    def __call__(self, text: str, **kwargs):
        if "prompt" in kwargs:
            raise TypeError("got an unexpected keyword argument 'prompt'")
        return super().__call__(text, **kwargs)


def test_retry_with_max_new_tokens_on_max_length_error() -> None:
    runtime = HFLocalRuntime(Settings())
    runner = LengthLimitedRunner()
    audio = runtime._run_pipeline({"kind": "pipeline", "runner": runner}, text="hello " * 40, config={})
    assert audio == b"\x00\x01\x02"
    assert any("max_new_tokens" in call or "generate_kwargs" in call for call in runner.calls[1:])


def test_prompt_typeerror_then_length_retry_still_succeeds() -> None:
    runtime = HFLocalRuntime(Settings())
    runner = PromptRejectingLengthRunner()
    audio = runtime._run_pipeline(
        {"kind": "pipeline", "runner": runner},
        text="vanakkam " * 35,
        config={"prompt": "energetic", "max_new_tokens": 384},
    )
    assert audio == b"\x00\x01\x02"
    assert any(call.get("max_new_tokens") == 384 for call in runner.calls)


class AmbiguousBoolAudio:
    def __bool__(self):
        raise ValueError("truth value is ambiguous")


def test_extract_audio_bytes_does_not_bool_eval_array_like_values() -> None:
    runtime = HFLocalRuntime(Settings())
    runtime._array_to_wav_bytes = lambda audio, sample_rate: b"\x10\x11"  # type: ignore[attr-defined]
    audio = runtime._extract_audio_bytes({"audio": AmbiguousBoolAudio(), "sampling_rate": 22050})
    assert audio == b"\x10\x11"


def test_extract_audio_bytes_handles_none_sampling_rate() -> None:
    runtime = HFLocalRuntime(Settings())
    runtime._array_to_wav_bytes = lambda audio, sample_rate: b"\x12\x13"  # type: ignore[attr-defined]
    audio = runtime._extract_audio_bytes({"audio": [0.1, -0.2], "sampling_rate": None})
    assert audio == b"\x12\x13"
