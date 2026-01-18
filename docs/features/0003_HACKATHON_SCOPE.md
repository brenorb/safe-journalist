# Feature 0003: Hackathon Scope - AI Summarization

**Goal**: Working demo that shows automatic AI summarization of journalist entries

---

## 🎯 PoC Must-Haves (Implement Now)

### 1. Storage Refactor (30 min)
**Why**: Foundation for everything else

```python
# storage.py - Add these functions:
- write_entry()           # /data/entries/<timestamp>-entry.md
- write_summary()         # /data/summaries/<timestamp>-summary.md
- list_entries()          # Get all entries sorted
- get_latest_summary()    # Get most recent summary or None
```

**Skip for now**: 
- `get_entries_since_timestamp()` - can filter in memory
- `count_entries_since_last_summary()` - can calculate inline

### 2. Basic Summarizer (45 min)
**Why**: Core feature - needs to work

```python
# summarizer.py - ONE function:
def generate_summary(session, api_key, model, base_dir, client):
    # 1. Get latest summary (if any)
    # 2. Get ALL entries (don't worry about filtering)
    # 3. Build simple prompt
    # 4. Call encrypted_openai_call
    # 5. Write summary
    # 6. Print/log result (simple print is fine)
```

**Skip for now**:
- Filtering entries by timestamp (just use all entries)
- Sophisticated prompt engineering
- Comprehensive error handling (just let it crash with good error messages)

### 3. Count-Based Trigger ONLY (30 min)
**Why**: Demonstrates automatic behavior, simpler than timers

```python
# api.py - Update create_entry:
@app.post("/entries", response_model=TextEntryOut)
async def create_entry(
    payload: TextEntryIn, 
    background_tasks: BackgroundTasks
):
    # 1. Write entry
    # 2. Count entries since last summary
    # 3. If count >= 3: background_tasks.add_task(run_summarization)
    # 4. Return response
```

**Skip for now**:
- Time-based trigger (complex async)
- Timer cancellation logic
- Debounce behavior

### 4. Simple Session Management (20 min)
**Why**: Need session to call AI

```python
# api.py - Add at module level:
_session_cache = {}

def get_or_create_session():
    if "session" not in _session_cache:
        client = httpx.Client(timeout=60.0)
        session = create_session(...)
        _session_cache["session"] = session
        _session_cache["client"] = client
    return _session_cache["session"], _session_cache["client"]
```

**Skip for now**:
- FastAPI lifespan events
- Proper client cleanup
- Session expiry handling
- Thread safety

### 5. Basic Error Handling (15 min)
**Why**: Don't want silent failures

```python
def run_summarization():
    try:
        generate_summary(...)
        print("✓ Summary generated!")
    except Exception as e:
        print(f"✗ Summarization failed: {e}")
```

**Skip for now**:
- Structured logging
- Error recovery
- Retry logic

---

## 📊 Demo Flow (What to Show)

```bash
# Terminal 1: Start API
uv run uvicorn safe_journalist.api:app

# Terminal 2: Create entries
curl -X POST http://localhost:8000/entries \
  -H "content-type: application/json" \
  -d '{"text":"Arrived at protest. 200+ people. Police present."}'

curl -X POST http://localhost:8000/entries \
  -H "content-type: application/json" \
  -d '{"text":"Tension rising. Police moving closer to crowd."}'

curl -X POST http://localhost:8000/entries \
  -H "content-type: application/json" \
  -d '{"text":"Police using tear gas. Moving to safe location."}'

# 👆 3rd entry triggers summarization automatically!

# Check results
ls data/entries/     # Shows 3 entry files
ls data/summaries/   # Shows 1 summary file
cat data/summaries/*.md  # Read the AI-generated summary
```

---

## ⚡ Quick Wins (If Time)

### Add manual trigger endpoint (10 min)
```python
@app.post("/summarize")
async def trigger_summarization():
    # Useful for demo/testing
    run_summarization()
    return {"status": "triggered"}
```

### Add status endpoint (10 min)
```python
@app.get("/status")
def get_status():
    entries = list_entries(DATA_DIR)
    summaries = list_summaries(DATA_DIR)
    return {
        "entries": len(entries),
        "summaries": len(summaries),
        "trigger_count": 3
    }
```

---

## 🚫 Explicitly Skip (Put in Roadmap)

### Time-Based Trigger
**Why skip**: Complex async, race conditions, timer cancellation
**Roadmap**: "Phase 2: Add debounce trigger (10s delay after last entry)"

### Sophisticated Error Recovery
**Why skip**: Takes time, not visible in demo
**Roadmap**: "Phase 2: Add retry logic and session refresh"

### Comprehensive Logging
**Why skip**: `print()` works fine for demo
**Roadmap**: "Phase 2: Structured logging with log levels"

### FastAPI Lifespan Management
**Why skip**: Module-level cache works for demo
**Roadmap**: "Phase 2: Proper client lifecycle management"

### Advanced Storage Features
**Why skip**: In-memory filtering works
**Roadmap**: "Phase 2: Optimize with timestamp-based filtering"

### Tests
**Why skip**: Manual testing sufficient for demo
**Roadmap**: "Phase 3: Add test suite (reference 0003_PRE_IMPLEMENT.md)"

---

## 📝 Roadmap (Post-Hackathon)

### Phase 2: Production Readiness
- [ ] Time-based trigger with debounce
- [ ] FastAPI lifespan for httpx.Client
- [ ] Structured logging
- [ ] Session expiry handling
- [ ] Comprehensive error recovery
- [ ] Environment variable validation

### Phase 3: Robustness
- [ ] Full test suite (see 0003_PRE_IMPLEMENT.md)
- [ ] Timer cancellation edge cases
- [ ] Race condition handling
- [ ] Performance optimization

### Phase 4: Features
- [ ] Web UI to view entries/summaries
- [ ] Configurable prompts
- [ ] Multiple AI models
- [ ] Summary history/versioning

---

## ⏱️ Time Budget (2.5 hours total)

| Task | Time | Priority |
|------|------|----------|
| Storage refactor | 30 min | MUST |
| Basic summarizer | 45 min | MUST |
| Count trigger | 30 min | MUST |
| Session management | 20 min | MUST |
| Error handling | 15 min | MUST |
| Manual trigger endpoint | 10 min | SHOULD |
| Status endpoint | 10 min | COULD |
| **TOTAL** | **2.5 hrs** | |

---

## 🎪 Demo Script

### Setup (Before Demo)
```bash
# 1. Set environment variables
export MAPLE_API_KEY="your-key"
export MAPLE_API_URL="https://enclave.trymaple.ai"
export DATA_DIR="./demo-data"

# 2. Clear data directory
rm -rf demo-data && mkdir -p demo-data

# 3. Start server
uv run uvicorn safe_journalist.api:app
```

### Demo Flow (During Presentation)

**1. Show the problem** (30 sec)
> "Journalist in dangerous situation sends check-ins. Emergency contacts need actionable summary, not 50 individual messages."

**2. Create entries** (1 min)
```bash
# Entry 1
curl -X POST http://localhost:8000/entries \
  -d '{"text":"Arrived at cartel-controlled border town. Meeting source at cafe."}'

# Entry 2  
curl -X POST http://localhost:8000/entries \
  -d '{"text":"Source confirms weapons shipment tonight. 10pm at warehouse."}'

# Entry 3 - TRIGGERS SUMMARIZATION
curl -X POST http://localhost:8000/entries \
  -d '{"text":"Being followed by two men. Moving to backup location."}'
```

**3. Show automatic summarization** (30 sec)
```bash
# Server logs show: "✓ Summary generated!"

# Show raw entries
ls -la demo-data/entries/

# Show AI summary
cat demo-data/summaries/*.md
```

**4. Explain the magic** (30 sec)
> "Every 3rd entry triggers encrypted AI call. Summary is concise, actionable, ready for emergency contacts. All data encrypted end-to-end."

**Total demo time**: ~3 minutes

---

## 🔥 Critical Simplifications for Hackathon

### Use Simple Counting
```python
# Don't overthink it - just count files
def count_entries_since_last_summary(base_dir):
    summaries = list_summaries(base_dir)
    if not summaries:
        # No summaries yet - count all entries
        return len(list_entries(base_dir))
    
    # Has summaries - get timestamp of latest
    latest = summaries[-1]  # Already sorted
    latest_ts = extract_timestamp(latest)
    
    # Count entries newer than latest summary
    entries = list_entries(base_dir)
    count = 0
    for entry in entries:
        if extract_timestamp(entry) > latest_ts:
            count += 1
    return count
```

### Use Simple Prompt
```python
# Don't overthink prompt engineering
def build_prompt(entries, last_summary=None):
    notes = "\n\n".join([f"- {p.read_text()}" for p in entries])
    
    if last_summary:
        return f"""Previous summary:
{last_summary}

New notes:
{notes}

Generate 3-5 bullet points with actionable information for emergency contacts."""
    else:
        return f"""Notes from journalist:
{notes}

Generate 3-5 bullet points with actionable information for emergency contacts."""
```

### Use Simple Module-Level Cache
```python
# Don't overthink lifecycle management
_SESSION = None
_CLIENT = None

def get_session():
    global _SESSION, _CLIENT
    if _SESSION is None:
        _CLIENT = httpx.Client(timeout=60.0)
        _SESSION = create_session(
            api_url=os.getenv("MAPLE_API_URL"),
            api_key=os.getenv("MAPLE_API_KEY"),
            client=_CLIENT
        )
    return _SESSION, _CLIENT
```

---

## ✅ Definition of Done (for PoC)

- [ ] Can create entries via API
- [ ] Entries stored in `/data/entries/<timestamp>-entry.md`
- [ ] After 3rd entry, summarization runs automatically
- [ ] Summary stored in `/data/summaries/<timestamp>-summary.md`
- [ ] Summary is readable AI-generated text
- [ ] Errors print to console (not silent)
- [ ] Can demo in < 3 minutes

**That's it! Everything else is roadmap.**

---

## 💡 Implementation Order

1. **Start with storage.py** - Get file structure working first
2. **Test storage manually** - Create dummy files, verify listing works
3. **Add summarizer.py** - Test with hardcoded prompt first
4. **Wire up API** - Connect everything together
5. **Test end-to-end** - Make 3 requests, verify summary generated
6. **Polish demo** - Clear data directory, prepare demo script

**Don't gold-plate. Ship the demo.**
