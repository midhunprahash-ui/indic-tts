from __future__ import annotations

import io
import wave

import pytest

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


def test_run_veena_decodes_snac_tokens() -> None:
    torch = pytest.importorskip("torch")
    runtime = HFLocalRuntime(Settings())

    audio_code_base_offset = 128266
    offsets = [audio_code_base_offset + i * 4096 for i in range(7)]
    veena_group = [offsets[0] + 1, offsets[1] + 2, offsets[2] + 3, offsets[3] + 4, offsets[4] + 5, offsets[5] + 6, offsets[6] + 7]

    class DummyTokenizer:
        pad_token_id = 0
        eos_token_id = 1

        @staticmethod
        def encode(prompt: str, add_special_tokens: bool = False):
            _ = (prompt, add_special_tokens)
            return [101, 102, 103]

    class DummyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.p = torch.nn.Parameter(torch.zeros(1))

        def generate(self, input_ids, **kwargs):
            _ = kwargs
            generated = torch.tensor([*veena_group, 128258], device=input_ids.device)
            return torch.cat([input_ids, generated.unsqueeze(0)], dim=1)

    class DummySNAC(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.p = torch.nn.Parameter(torch.zeros(1))

        def decode(self, hierarchical_codes):
            _ = hierarchical_codes
            return torch.linspace(-0.5, 0.5, steps=480, device=self.p.device).unsqueeze(0)

    wav = runtime._run_veena(
        {"model": DummyModel(), "tokenizer": DummyTokenizer(), "snac_model": DummySNAC()},
        text="Hello Tanglish world",
        config={"speaker": "kavya", "max_new_tokens": 64},
    )
    assert isinstance(wav, bytes)
    assert len(wav) > 44


def test_run_parler_uses_main_text_as_prompt_and_style_as_description_hint() -> None:
    torch = pytest.importorskip("torch")
    runtime = HFLocalRuntime(Settings())

    class DummyTokenizer:
        def __init__(self):
            self.calls: list[str] = []

        def __call__(self, text: str, return_tensors: str = "pt"):
            _ = return_tensors
            self.calls.append(text)
            length = max(1, len(text.split()))
            return type(
                "TokenBatch",
                (),
                {
                    "input_ids": torch.ones((1, length), dtype=torch.int64),
                    "attention_mask": torch.ones((1, length), dtype=torch.int64),
                },
            )()

    class DummyParlerModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.p = torch.nn.Parameter(torch.zeros(1))
            self.config = type("Cfg", (), {"sampling_rate": 24000})()
            self.last_generate_kwargs: dict | None = None

        def generate(self, **kwargs):
            self.last_generate_kwargs = kwargs
            # 240 samples at 24kHz => ~0.01s, enough for conversion validation.
            return torch.linspace(-0.2, 0.2, steps=240).unsqueeze(0)

    tokenizer = DummyTokenizer()
    model = DummyParlerModel()

    wav = runtime._run_parler(
        {"model": model, "tokenizer": tokenizer, "device": "cpu"},
        text="This exact sentence should be spoken",
        config={
            "description": "Warm female Tanglish voice",
            "prompt": "energetic and cheerful",
        },
    )

    assert len(tokenizer.calls) == 2
    # First tokenizer call is description path with appended style hint.
    assert "Warm female Tanglish voice" in tokenizer.calls[0]
    assert "energetic and cheerful" in tokenizer.calls[0]
    # Second tokenizer call must be the center input text (not style hint).
    assert tokenizer.calls[1] == "This exact sentence should be spoken"
    assert isinstance(wav, bytes)
    assert len(wav) > 44


def test_array_to_wav_bytes_preserves_stereo_shape() -> None:
    np = pytest.importorskip("numpy")
    # Shape (channels, samples) as commonly returned by some TTS runtimes.
    stereo = np.vstack(
        [
            np.linspace(-0.5, 0.5, num=2400, dtype=np.float32),
            np.linspace(0.5, -0.5, num=2400, dtype=np.float32),
        ]
    )
    wav_bytes = HFLocalRuntime._array_to_wav_bytes(stereo, 24000)
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 2
        # 2400 frames at 24kHz -> 0.1 seconds.
        assert wf.getnframes() == 2400
        assert wf.getframerate() == 24000
