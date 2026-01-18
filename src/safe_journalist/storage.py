from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def generate_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_text_markdown(text: str, base_dir: str, timestamp: str) -> Path:
    data_dir = Path(base_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{timestamp}.md"
    path.write_text(text, encoding="utf-8")
    return path


def write_entry(text: str, base_dir: str, timestamp: str) -> Path:
    """Write an entry to /data/entries/<timestamp>-entry.md"""
    entries_dir = Path(base_dir) / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)
    path = entries_dir / f"{timestamp}-entry.md"
    path.write_text(text, encoding="utf-8")
    return path


def write_summary(summary: str, base_dir: str, timestamp: str) -> Path:
    """Write a summary to /data/summaries/<timestamp>-summary.md"""
    summaries_dir = Path(base_dir) / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    path = summaries_dir / f"{timestamp}-summary.md"
    path.write_text(summary, encoding="utf-8")
    return path


def list_entries(base_dir: str) -> list[Path]:
    """List all entries sorted by timestamp (oldest to newest)"""
    entries_dir = Path(base_dir) / "entries"
    if not entries_dir.exists():
        return []
    entries = sorted(entries_dir.glob("*-entry.md"))
    return entries


def list_summaries(base_dir: str) -> list[Path]:
    """List all summaries sorted by timestamp (oldest to newest)"""
    summaries_dir = Path(base_dir) / "summaries"
    if not summaries_dir.exists():
        return []
    summaries = sorted(summaries_dir.glob("*-summary.md"))
    return summaries


def get_latest_summary(base_dir: str) -> tuple[Path, str] | None:
    """Get the most recent summary file path and content, or None if no summaries exist"""
    summaries = list_summaries(base_dir)
    if not summaries:
        return None
    latest = summaries[-1]
    content = latest.read_text(encoding="utf-8")
    return latest, content


def count_entries_since_last_summary(base_dir: str) -> int:
    """Count entries created after the most recent summary (or all entries if no summaries)"""
    entries = list_entries(base_dir)
    if not entries:
        return 0
    
    latest_summary = get_latest_summary(base_dir)
    if latest_summary is None:
        # No summaries yet - count all entries
        return len(entries)
    
    # Extract timestamp from summary filename
    summary_path, _ = latest_summary
    summary_timestamp = summary_path.stem.replace("-summary", "")
    
    # Count entries newer than summary
    count = 0
    for entry in entries:
        entry_timestamp = entry.stem.replace("-entry", "")
        if entry_timestamp > summary_timestamp:
            count += 1
    
    return count
