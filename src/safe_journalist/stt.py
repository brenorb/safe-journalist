from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


class SttNotConfiguredError(RuntimeError):
    pass


class SttDependencyError(RuntimeError):
    pass


class SttTranscriptionError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionResult:
    text: str


def _get_stt_model_id() -> str:
    model_id = os.getenv("STT_MODEL")
    if not model_id:
        raise SttNotConfiguredError(
            "STT_MODEL is not set. Set STT_MODEL to a Parakeet model id (e.g. a HuggingFace repo)."
        )
    return model_id


@lru_cache(maxsize=1)
def _get_asr_pipeline():
    try:
        import torch
        from transformers import pipeline
    except Exception as e:  # pragma: no cover
        raise SttDependencyError(
            "Missing STT dependencies. Install extras: `uv sync --extra stt`"
        ) from e

    model_id = _get_stt_model_id()

    device = "cpu"
    if torch.cuda.is_available():
        device = 0
    elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        device = "mps"

    return pipeline(
        task="automatic-speech-recognition",
        model=model_id,
        device=device,
    )


def transcribe_audio_bytes(audio_bytes: bytes) -> TranscriptionResult:
    if not audio_bytes:
        raise SttTranscriptionError("audio is empty")

    try:
        import io

        import torchaudio
    except Exception as e:  # pragma: no cover
        raise SttDependencyError(
            "Missing audio dependencies. Install extras: `uv sync --extra stt`"
        ) from e

    asr = _get_asr_pipeline()

    try:
        waveform, sample_rate = torchaudio.load(io.BytesIO(audio_bytes))
        if sample_rate != 16000:
            waveform = torchaudio.functional.resample(waveform, sample_rate, 16000)
            sample_rate = 16000

        # ASR pipeline accepts dict with raw audio.
        result = asr({"raw": waveform.squeeze().numpy(), "sampling_rate": sample_rate})
    except Exception as e:
        raise SttTranscriptionError(f"Failed to transcribe audio: {e}") from e

    text = ""
    if isinstance(result, dict):
        text = str(result.get("text", "")).strip()
    else:
        text = str(result).strip()

    if not text:
        raise SttTranscriptionError("Transcription produced empty text")

    return TranscriptionResult(text=text)
