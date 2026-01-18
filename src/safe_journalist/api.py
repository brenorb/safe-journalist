from __future__ import annotations

import os

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from safe_journalist import storage, summarizer
from safe_journalist.session import MapleSession, create_session


class TextEntryIn(BaseModel):
    text: str


class TextEntryOut(BaseModel):
    path: str
    timestamp: str


class AlertOut(BaseModel):
    summary: str
    timestamp: str
    path: str


def get_data_dir() -> str:
    return os.getenv("DATA_DIR", "/data")


def get_summary_trigger_count() -> int:
    return int(os.getenv("SUMMARY_TRIGGER_COUNT", "3"))


# Module-level session cache
_SESSION_CACHE: dict[str, MapleSession | httpx.Client] = {}


def get_or_create_session() -> tuple[MapleSession, httpx.Client]:
    """Get or create a cached MapleSession and httpx.Client"""
    if "session" not in _SESSION_CACHE:
        api_url = os.getenv("MAPLE_API_URL", "https://enclave.trymaple.ai").rstrip("/")
        api_key = os.getenv("MAPLE_API_KEY")
        
        if not api_key:
            raise ValueError("MAPLE_API_KEY environment variable is not set")
        
        client = httpx.Client(timeout=60.0)
        session = create_session(api_url=api_url, api_key=api_key, client=client)
        
        _SESSION_CACHE["session"] = session
        _SESSION_CACHE["client"] = client
    
    return _SESSION_CACHE["session"], _SESSION_CACHE["client"]  # type: ignore


def run_summarization() -> None:
    """Run summarization in background - handles errors gracefully"""
    try:
        api_key = os.getenv("MAPLE_API_KEY")
        if not api_key:
            print("⚠ Skipping summarization: MAPLE_API_KEY not set")
            return
        
        model = os.getenv("MAPLE_MODEL", "llama-3.3-70b")
        base_dir = get_data_dir()
        
        session, client = get_or_create_session()
        result = summarizer.generate_summary(
            session=session,
            api_key=api_key,
            model=model,
            base_dir=base_dir,
            client=client,
        )
        
        if result:
            print(f"✓ Summary generated!")
        else:
            print("ℹ No entries to summarize")
    except Exception as e:
        print(f"✗ Summarization failed: {e}")


app = FastAPI()


@app.post("/entries", response_model=TextEntryOut)
def create_entry(payload: TextEntryIn, background_tasks: BackgroundTasks) -> TextEntryOut:
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="text must be a non-empty string")

    timestamp = storage.generate_timestamp()
    base_dir = get_data_dir()
    
    # Write entry using new storage function
    path = storage.write_entry(
        text=payload.text,
        base_dir=base_dir,
        timestamp=timestamp,
    )
    
    # Check if we should trigger summarization (count-based)
    count = storage.count_entries_since_last_summary(base_dir)
    trigger_count = get_summary_trigger_count()
    
    if count >= trigger_count:
        print(f"Triggering summarization: {count} entries since last summary (threshold: {trigger_count})")
        background_tasks.add_task(run_summarization)
    
    return TextEntryOut(path=str(path), timestamp=timestamp)


@app.post("/summarize")
def trigger_summarization(background_tasks: BackgroundTasks) -> dict:
    """Manually trigger summarization (useful for demo/testing)"""
    base_dir = get_data_dir()
    entries = storage.list_entries(base_dir)
    
    if not entries:
        return {"status": "no_entries", "message": "No entries to summarize"}
    
    background_tasks.add_task(run_summarization)
    return {"status": "triggered", "message": "Summarization started in background"}


@app.get("/status")
def get_status() -> dict:
    """Get status of entries and summaries"""
    base_dir = get_data_dir()
    entries = storage.list_entries(base_dir)
    summaries = storage.list_summaries(base_dir)
    count_since_last = storage.count_entries_since_last_summary(base_dir)
    trigger_count = get_summary_trigger_count()
    
    return {
        "entries": len(entries),
        "summaries": len(summaries),
        "entries_since_last_summary": count_since_last,
        "trigger_count": trigger_count,
        "will_trigger_on_next_entry": count_since_last >= trigger_count,
    }


@app.get("/alert", response_model=AlertOut)
def get_alert() -> AlertOut:
    """Get the latest summary for emergency contacts"""
    base_dir = get_data_dir()
    result = storage.get_latest_summary(base_dir)
    
    if result is None:
        raise HTTPException(status_code=404, detail="No summary available yet")
    
    summary_path, summary_content = result
    # Extract timestamp from filename: "20260117T123456Z-summary.md" -> "20260117T123456Z"
    timestamp = summary_path.stem.replace("-summary", "")
    
    return AlertOut(
        summary=summary_content,
        timestamp=timestamp,
        path=str(summary_path),
    )
