from __future__ import annotations

import os
import tempfile
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
            "STT_MODEL is not set. Set STT_MODEL to a Parakeet model id (e.g. "
            "`nvidia/parakeet-tdt-0.6b-v2`)."
        )
    return model_id


@lru_cache(maxsize=1)
def _get_parakeet_model():
    try:
        # NeMo uses torch under the hood.
        import torch
        from nemo.collections.asr.models import ASRModel
    except Exception as e:  # pragma: no cover
        raise SttDependencyError(
            "Missing Parakeet STT dependencies. Install extras: `uv sync --extra stt`"
        ) from e

    model_id = _get_stt_model_id()

    try:
        model = ASRModel.from_pretrained(model_name=model_id)
    except Exception as e:
        raise SttDependencyError(f"Failed to load Parakeet model '{model_id}': {e}") from e

    # Move to best available device.
    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
    elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        device = "mps"

    try:
        model = model.to(device)
    except Exception:
        # Some NeMo models don't implement .to() fully; keep default.
        pass

    model.eval()
    return model


def transcribe_audio_bytes(audio_bytes: bytes, *, suffix: str = ".wav") -> TranscriptionResult:
    if not audio_bytes:
        raise SttTranscriptionError("audio is empty")

    model = _get_parakeet_model()

    # NeMo's transcription helpers expect file paths.
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            texts = model.transcribe([tmp.name])
    except Exception as e:
        raise SttTranscriptionError(f"Failed to transcribe audio: {e}") from e

    text = ""
    if isinstance(texts, list) and texts:
        text = str(texts[0]).strip()
    else:
        text = str(texts).strip()

    if not text:
        raise SttTranscriptionError("Transcription produced empty text")

    return TranscriptionResult(text=text)
