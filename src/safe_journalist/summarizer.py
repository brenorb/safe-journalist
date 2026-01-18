from __future__ import annotations

from pathlib import Path

import httpx

from safe_journalist import storage
from safe_journalist.client import encrypted_openai_call
from safe_journalist.session import MapleSession


def generate_summary(
    session: MapleSession,
    api_key: str,
    model: str,
    base_dir: str,
    client: httpx.Client,
) -> tuple[Path, str] | None:
    """Generate AI summary of entries, considering previous summary if exists.
    
    Returns:
        Tuple of (summary_path, summary_content) or None if no entries to summarize
    """
    # Get all entries
    entries = storage.list_entries(base_dir)
    if not entries:
        print("No entries to summarize")
        return None
    
    # Check if there's a previous summary
    latest_summary = storage.get_latest_summary(base_dir)
    
    if latest_summary:
        # Get entries newer than the last summary
        summary_path, summary_content = latest_summary
        summary_timestamp = summary_path.stem.replace("-summary", "")
        
        # Filter entries to only those after the summary
        new_entries = []
        for entry in entries:
            entry_timestamp = entry.stem.replace("-entry", "")
            if entry_timestamp > summary_timestamp:
                new_entries.append(entry)
        
        # Build prompt with previous summary
        entries_text = "\n\n".join([f"- {p.read_text(encoding='utf-8')}" for p in new_entries])
        prompt = f"""Previous summary:
{summary_content}

New notes:
{entries_text}

Generate a concise 3-5 bullet summary with the most relevant and up to date actionable information for emergency contacts."""
    else:
        # No previous summary - use all entries
        entries_text = "\n\n".join([f"- {p.read_text(encoding='utf-8')}" for p in entries])
        prompt = f"""Notes from journalist:
{entries_text}

Generate a concise 3-5 bullet summary with the most relevant and up to date actionable information for emergency contacts."""
    
    # Call AI with encrypted request
    print(f"Calling AI to generate summary...")
    result = encrypted_openai_call(
        session=session,
        api_key=api_key,
        path="/v1/chat/completions",
        payload={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        client=client,
    )
    
    # Extract summary text from response
    summary_text = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    
    # Write summary to disk
    timestamp = storage.generate_timestamp()
    summary_path = storage.write_summary(summary_text, base_dir, timestamp)
    
    print(f"✓ Summary generated: {summary_path}")
    return summary_path, summary_text
