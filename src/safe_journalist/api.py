from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from safe_journalist import storage, summarizer
from safe_journalist.session import MapleSession, create_session

# Load environment variables from .env file
load_dotenv()


class TextEntryIn(BaseModel):
    text: str


class TextEntryOut(BaseModel):
    path: str
    timestamp: str


class AlertOut(BaseModel):
    summary: str
    timestamp: str
    path: str


class EntryOut(BaseModel):
    timestamp: str
    preview: str
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

# Mount static files for CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root() -> FileResponse:
    """Serve the frontend HTML"""
    return FileResponse("static/index.html")


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


@app.get("/entries", response_model=list[EntryOut])
def list_entries_endpoint(limit: int = 10) -> list[EntryOut]:
    """List recent entries (newest first)"""
    # Validate limit parameter
    if limit <= 0 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100"
        )
    
    base_dir = get_data_dir()
    all_entries = storage.list_entries(base_dir)
    
    # Take last N entries (newest) and reverse for newest-first order
    recent_entries = all_entries[-limit:] if len(all_entries) > limit else all_entries
    recent_entries = list(reversed(recent_entries))
    
    # Build response
    result = []
    for entry_path in recent_entries:
        # Extract timestamp from filename: "20260117T123456Z-entry.md" -> "20260117T123456Z"
        timestamp = entry_path.stem.replace("-entry", "")
        
        # Read content and truncate to 200 chars for preview
        content = entry_path.read_text(encoding="utf-8")
        preview = content[:200]
        
        result.append(EntryOut(
            timestamp=timestamp,
            preview=preview,
            path=str(entry_path),
        ))
    
    return result


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
