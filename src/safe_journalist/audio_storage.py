from __future__ import annotations

from pathlib import Path


def write_audio_entry(audio_bytes: bytes, base_dir: str, timestamp: str, *, extension: str) -> Path:
    """Write audio to /data/entries/audio/<timestamp>-audio.<ext>"""
    audio_dir = Path(base_dir) / "entries" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    ext = (extension or "").lstrip(".").lower() or "webm"
    path = audio_dir / f"{timestamp}-audio.{ext}"
    path.write_bytes(audio_bytes)
    return path
