# Feature 0003: Pre-Implementation Check - AI Summarization

**Date**: 2026-01-18  
**Feature**: Automatic AI Summarization with Hybrid Triggers

---

## ⚠️ Component Risk Assessment

### HIGH SEVERITY: Test Pattern Issue

**TemporaryDirectory Context Manager Scope Bug**
- **Source**: `docs/solutions/test-failures/temporary-directory-context-scope.md`
- **Issue**: When writing tests for new storage functions, ensure file system assertions stay inside `TemporaryDirectory` context
- **Impact**: Tests for `list_entries()`, `list_summaries()`, `count_entries_since_last_summary()` must handle temp dirs correctly
- **Example**:
  ```python
  # ❌ BAD - Directory deleted before assertion
  def test_list_entries():
      with TemporaryDirectory() as tmpdir:
          storage.write_entry(...)
      # tmpdir deleted here!
      entries = storage.list_entries(tmpdir)  # FAILS
  
  # ✅ GOOD - Assertions inside context
  def test_list_entries():
      with TemporaryDirectory() as tmpdir:
          storage.write_entry(...)
          entries = storage.list_entries(tmpdir)  # ✓ Works
          assert len(entries) == 1
  ```

### MEDIUM SEVERITY: Module Organization

**Separation of Concerns Pattern**
- **Source**: `docs/solutions/code-organization/monolithic-module-refactor.md`
- **Pattern**: Creating new `summarizer.py` module follows established pattern of focused modules
- **Guideline**: Keep single responsibility - summarizer.py handles only summarization logic

### LOW SEVERITY: Known Issues

**COSE Array Validation** (attestation.py)
- **Location**: `src/safe_journalist/attestation.py:17-18`
- **Issue**: Accepts 3+ elements instead of exactly 4
- **Status**: Documented, not blocking your feature

### Components You'll Modify

#### storage.py
- **Current state**: Simple (17 lines)
- **Changes**: Adding 7 new functions
- ✓ No known issues
- ⚠️ Will grow significantly - monitor for future refactoring triggers (>200 lines)

#### api.py
- **Current state**: Simple (39 lines)
- **Changes**: Adding session management + background tasks
- ✓ No known issues
- ⚠️ Will add complexity: module-level state, async tasks, timer cancellation

#### summarizer.py (NEW)
- **Type**: New module for core feature logic
- ✓ Clean slate, no existing issues
- ⚠️ Will handle encryption, file I/O, AI calls - multiple failure modes

---

## 📚 Related Patterns

### 1. Module Architecture (APPLICABLE)

**Source**: `docs/solutions/code-organization/monolithic-module-refactor.md`

**Pattern**: Focused modules with single responsibility
- ✅ Your plan creates `summarizer.py` as a focused module - good!
- ✅ Separates storage operations from API logic
- ⚠️ Watch api.py complexity: adding session cache, timer state, background tasks

**Key principle**: "Each module handles one concern"
- `storage.py` → file operations
- `api.py` → HTTP endpoints + coordination
- `summarizer.py` → AI summarization logic

**Refactoring triggers to watch**:
- ⚠️ File exceeds 200 lines
- ⚠️ More than 3 distinct concerns
- ⚠️ Difficult to write focused unit tests

### 2. HTTP Client Management (NEEDS ATTENTION)

**Current pattern**: `httpx.Client` passed as parameter in `cli.py`

```python
# cli.py:20-21
with httpx.Client(timeout=60.0) as client:
    session = create_session(api_url=api_url, api_key=api_key, client=client)
```

**Your plan**: Module-level or lifespan-managed httpx client

**⚠️ Gap**: No existing FastAPI lifespan pattern in codebase
- Current code uses context managers
- Your implementation will introduce first module-level HTTP client
- **Consider**: FastAPI lifespan events vs module-level client

**Recommendation**: Use FastAPI lifespan events for proper startup/shutdown

### 3. Error Handling (APPLICABLE)

**Current pattern**: `raise_for_status()` + let exceptions bubble

```python
# client.py:31, session.py:26,41
resp.raise_for_status()  # Raises HTTPStatusError on 4xx/5xx
```

**For background tasks**: Can't bubble up - must catch and log
- Background tasks run after response is sent
- Failures won't be visible to client
- **Critical**: Add comprehensive logging in `summarizer.py`

**Required pattern**:
```python
def run_summarization_background():
    try:
        generate_summary(...)
    except httpx.HTTPStatusError as e:
        logger.error(f"Summarization HTTP error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        # Don't crash the server!
```

### 4. Session Creation Flow (APPLICABLE)

**Current pattern**: `create_session()` → attestation → key exchange → decrypt

```python
# From session.py
create_session(api_url=api_url, api_key=api_key, client=client)
# Returns MapleSession with decrypted session_key
```

**For caching**: Session is immutable (frozen dataclass)
- ✅ Safe to cache at module level
- ⚠️ Need strategy for session expiry/refresh (not currently handled)
- ⚠️ `httpx.Client` must remain open while cached session is in use

---

## ✅ Prevention Strategies

### From Test Failures Documentation

#### 1. Context Manager Scope (HIGH PRIORITY)

**Use reusable fixture pattern**:
```python
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from unittest.mock import patch

@contextmanager
def temp_data_dir():
    with TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
            yield tmpdir
        # Directory still exists here for assertions

# Usage in tests
def test_list_entries():
    with temp_data_dir() as tmpdir:
        # All test code and assertions here
        storage.write_entry(...)
        entries = storage.list_entries(tmpdir)
        assert len(entries) == 1
```

### From Module Refactoring Documentation

#### 2. Module Complexity Monitoring

Watch for these triggers:
- [ ] File exceeds 200 lines → Consider splitting
- [ ] More than 3 distinct concerns → Refactor
- [ ] Difficult to write focused unit tests → Design issue

#### 3. Clear Module Boundaries

```python
# summarizer.py should ONLY handle:
# - Reading entries/summaries from disk
# - Constructing AI prompts
# - Calling encrypted_openai_call
# - Writing summary to disk
# - Logging

# summarizer.py should NOT handle:
# - HTTP client lifecycle
# - Session creation/caching
# - API endpoint logic
# - Timer management
```

### New Patterns for This Feature

#### 4. Background Task Error Handling (CRITICAL)

```python
import logging

logger = logging.getLogger(__name__)

def run_summarization_background():
    """Background task - must catch all exceptions."""
    try:
        generate_summary(...)
        logger.info("Summarization completed successfully")
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Summarization HTTP error: {e.response.status_code}",
            extra={"status_code": e.response.status_code}
        )
    except httpx.RequestError as e:
        logger.error(f"Summarization network error: {e}")
    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        # Don't crash the server!
```

#### 5. Timer Cancellation Safety (CRITICAL)

```python
import asyncio
from typing import Optional

# Module-level state needs thread-safety
_pending_summary_task: Optional[asyncio.Task] = None
_task_lock = asyncio.Lock()

async def cancel_pending_task():
    """Safely cancel any pending summarization task."""
    async with _task_lock:
        global _pending_summary_task
        if _pending_summary_task and not _pending_summary_task.done():
            _pending_summary_task.cancel()
            try:
                await _pending_summary_task
            except asyncio.CancelledError:
                pass  # Expected
            _pending_summary_task = None
```

#### 6. File Listing Robustness

```python
from pathlib import Path

def list_entries(base_dir: str) -> list[Path]:
    """List all entry files, handling missing directories gracefully."""
    entries_dir = Path(base_dir) / "entries"
    if not entries_dir.exists():
        return []  # Not an error - just no entries yet
    return sorted(entries_dir.glob("*-entry.md"))

def list_summaries(base_dir: str) -> list[Path]:
    """List all summary files, handling missing directories gracefully."""
    summaries_dir = Path(base_dir) / "summaries"
    if not summaries_dir.exists():
        return []  # Not an error - just no summaries yet
    return sorted(summaries_dir.glob("*-summary.md"))
```

#### 7. Timestamp Extraction Safety

```python
from pathlib import Path

def extract_timestamp(path: Path) -> str:
    """
    Extract timestamp from filename.
    
    Examples:
        "20260118T123456Z-entry.md" → "20260118T123456Z"
        "20260118T123456Z-summary.md" → "20260118T123456Z"
    """
    filename = path.stem  # Remove .md extension
    parts = filename.split("-", maxsplit=1)
    if len(parts) < 2:
        raise ValueError(f"Invalid filename format: {filename}")
    return parts[0]  # "20260118T123456Z"
```

#### 8. FastAPI Lifespan Pattern (RECOMMENDED)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx

# Module-level variables
_http_client: Optional[httpx.Client] = None
_maple_session: Optional[MapleSession] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage httpx client lifecycle."""
    global _http_client, _maple_session
    
    # Startup
    _http_client = httpx.Client(timeout=60.0)
    logger.info("HTTP client initialized")
    
    # Optionally initialize session if API key available
    api_key = os.getenv("MAPLE_API_KEY")
    if api_key:
        try:
            _maple_session = create_session(
                api_url=os.getenv("MAPLE_API_URL", "https://enclave.trymaple.ai"),
                api_key=api_key,
                client=_http_client
            )
            logger.info("Maple session initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Maple session: {e}")
    
    yield
    
    # Shutdown
    if _http_client:
        _http_client.close()
        logger.info("HTTP client closed")

app = FastAPI(lifespan=lifespan)
```

---

## 🔗 Dependency Analysis

### Direct Dependencies (Components You'll Use)

#### storage.py (you're modifying)
- ✓ No known issues
- ✓ Simple current implementation
- ⚠️ Growing from 17 to ~100+ lines

#### session.py (you'll use create_session)
- ✓ No known issues
- ✓ Tested and working
- ⚠️ No session expiry handling - cached sessions may become stale

#### client.py (you'll use encrypted_openai_call)
- ✓ No known issues
- ✓ Error handling via `raise_for_status()`
- ⚠️ Requires open `httpx.Client` - lifespan critical

#### attestation.py (indirect via session.py)
- ⚠️ Known issue: COSE validation (low severity, not blocking)

### New Dependencies to Add

#### asyncio (for timer-based triggers)
- New to this codebase
- **Risk**: No existing async patterns to follow
- **Recommendation**: Use FastAPI's BackgroundTasks for delayed execution

#### logging (for background task debugging)
- Not currently used in codebase
- **Critical** for debugging background operations
- **Recommendation**: Add structured logging from the start

```python
import logging

# Configure at module level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

---

## 💡 Recommendations

### CRITICAL Actions Before Implementation

#### 1. Design Timer Cancellation Strategy
- ⚠️ No existing async task management in codebase
- **Option A**: Use `asyncio.create_task` with task tracking
- **Option B**: FastAPI's BackgroundTasks with external scheduler (e.g., APScheduler)
- **Recommendation**: Start with Option A (simpler, built-in)

#### 2. Plan httpx.Client Lifecycle
- ⚠️ Current code uses context managers, not module-level clients
- **Recommendation**: Use FastAPI lifespan events (app startup/shutdown)
- Must keep client open while cached session is active
- Handle graceful shutdown (cancel pending tasks, close connections)

#### 3. Add Comprehensive Logging
- ⚠️ Background tasks fail silently without logs
- **Log events**:
  - Entry creation
  - Trigger decisions (count vs time)
  - Timer scheduling/cancellation
  - Summarization start/completion
  - AI call success/failure
  - File writes
- Use structured logging with context (entry count, timestamp)

#### 4. Design Session Expiry Strategy
- ⚠️ `MapleSession` has no TTL or refresh mechanism
- **Question**: What happens if cached session expires during summarization?
- **Options**:
  - Lazy refresh on failure (catch error, recreate session, retry)
  - Periodic recreation (e.g., every N minutes)
  - Session per summarization (no caching)
- **Recommendation**: Start simple (lazy refresh on failure)

### HIGH Priority

#### 5. Write Tests with Proper Context Manager Scope
- **Must review**: `docs/solutions/test-failures/temporary-directory-context-scope.md`
- Use `temp_data_dir` fixture pattern for all storage tests
- Test all new storage functions: `list_entries`, `list_summaries`, `get_latest_summary`, etc.

#### 6. Handle Missing MAPLE_API_KEY Gracefully
- Log warning at startup if missing
- Disable auto-summarization (entries still work)
- Don't crash the server
- Return helpful error if manually triggered

```python
if not os.getenv("MAPLE_API_KEY"):
    logger.warning("MAPLE_API_KEY not set - auto-summarization disabled")
    SUMMARIZATION_ENABLED = False
```

#### 7. Test Timer Cancellation Edge Cases
- What if timer fires during another summarization?
- What if count threshold reached while timer pending?
- Race conditions between timer and count trigger?
- Multiple rapid entries resetting timer repeatedly

### MEDIUM Priority

#### 8. Monitor api.py Complexity
- Adding: session cache, httpx client, timer state, background tasks
- Current: 39 lines
- After: Likely 200+ lines
- **Consider**: Extract timer logic to separate `scheduler.py` module if needed

#### 9. Plan for Empty/No-Entry Scenarios
- What if summarize triggered but no entries exist?
- What if all entries are empty strings?
- **Recommendation**: Graceful no-op with logging

```python
if not entries:
    logger.info("No entries to summarize, skipping")
    return None
```

#### 10. Document the Debounce Behavior
- "Timer resets on each new entry" is complex
- Add docstring explaining the trigger logic
- **Consider**: Add `GET /summarization/status` endpoint to show:
  - Last summary timestamp
  - Entries since last summary
  - Pending timer (time remaining)

---

## 📋 Implementation Checklist

### Before Writing Code
- [ ] Understand TemporaryDirectory scope issue for tests
- [ ] Design httpx.Client + MapleSession caching strategy
- [ ] Design timer cancellation with proper locking
- [ ] Plan logging strategy for background tasks
- [ ] Review separation of concerns pattern
- [ ] Read `docs/solutions/test-failures/temporary-directory-context-scope.md`
- [ ] Read `docs/solutions/code-organization/monolithic-module-refactor.md`

### During Implementation

#### Storage Layer
- [ ] Keep functions focused (single responsibility)
- [ ] Handle missing directories gracefully (empty lists, not errors)
- [ ] Add type hints for all functions
- [ ] Write docstrings with examples

#### API Layer
- [ ] Add FastAPI lifespan for httpx.Client
- [ ] Cache MapleSession at module level
- [ ] Implement timer with proper cancellation
- [ ] Add comprehensive error handling in background tasks
- [ ] Use structured logging with context

#### Summarizer Layer
- [ ] Keep module focused (only summarization logic)
- [ ] Add comprehensive error handling
- [ ] Log all important events
- [ ] Handle empty entry scenarios
- [ ] Test AI prompt construction

#### Testing
- [ ] Use temp_data_dir fixture pattern
- [ ] Test all storage functions
- [ ] Test timer cancellation edge cases
- [ ] Test missing MAPLE_API_KEY scenario
- [ ] Test background task error handling
- [ ] Test file naming conventions

### After Implementation
- [ ] Verify background task errors are logged, not silent
- [ ] Test session expiry scenario
- [ ] Verify file naming conventions are clear and consistent
- [ ] Check api.py complexity (<200 lines)
- [ ] Run full test suite
- [ ] Manual testing: create entries, observe summarization

---

## 🏷️ Relevant Tags

Based on your work, these tags apply:
- `asyncio` `background-tasks` `fastapi` `file-operations`
- `session-management` `error-handling` `timer-debounce`
- `ai-integration` `encryption` `storage-refactor`
- `context-managers` `testing` `logging`

---

## 📚 Must-Read Documentation

### Before Starting

1. **docs/solutions/test-failures/temporary-directory-context-scope.md**
   - Critical for writing correct tests
   - Learn fixture pattern for temp directories

2. **docs/solutions/code-organization/monolithic-module-refactor.md**
   - Understand module design principles
   - Learn separation of concerns pattern

### Reference During Implementation

3. **src/safe_journalist/client.py**
   - `encrypted_openai_call` signature and error handling
   - HTTP request patterns

4. **src/safe_journalist/session.py**
   - `create_session` flow and MapleSession structure
   - Attestation and key exchange patterns

---

## 🚨 Key Risks to Mitigate

### CRITICAL Risks

1. **Background task error handling**
   - Silent failures will be invisible
   - Must catch all exceptions
   - Must log comprehensively

2. **Timer cancellation race conditions**
   - Multiple requests could create race conditions
   - Need proper locking/synchronization
   - Test edge cases thoroughly

3. **httpx.Client lifecycle management**
   - Client must stay open while session is cached
   - Improper shutdown could leak connections
   - Use FastAPI lifespan events

### HIGH Risks

4. **Test context manager scope**
   - Easy to write tests that pass locally but are incorrect
   - Review documentation before writing tests
   - Use fixture pattern consistently

5. **Session expiry handling**
   - Cached sessions may become stale
   - Need retry logic for encryption failures
   - Consider session TTL

---

## 🎯 Phased Implementation Approach

Consider implementing in phases to reduce compound risk:

### Phase 1: Storage Refactor (Low Risk, Foundational)
- Refactor data directory structure (`/entries`, `/summaries`)
- Implement all storage functions
- Write comprehensive tests
- **Risk**: Low - pure file operations
- **Benefit**: Foundation for everything else

### Phase 2: Synchronous Summarization (Test Core Logic)
- Create `summarizer.py` with basic `generate_summary`
- Test AI prompt construction
- Test encrypted call integration
- **Risk**: Medium - but no async complexity yet
- **Benefit**: Verify core logic works

### Phase 3: Count-Based Trigger (Simpler Trigger)
- Add session caching to api.py
- Implement immediate count-based trigger
- Use BackgroundTasks for async execution
- **Risk**: Medium - first background task
- **Benefit**: Working feature without timer complexity

### Phase 4: Time-Based Trigger (Complex Async Logic)
- Add timer scheduling and cancellation
- Implement debounce behavior
- Handle race conditions
- **Risk**: High - most complex piece
- **Benefit**: Complete feature

This approach allows testing each piece independently and reduces compound risk.

---

## ⚡ Quick Reference

### Biggest Gaps in Current Codebase
- No existing async/background task patterns
- No module-level HTTP client management  
- No logging infrastructure
- No timer/scheduling patterns

### Most Critical Prevention Strategies
1. Comprehensive logging in background tasks
2. Proper timer cancellation with locking
3. Test context manager scope
4. httpx.Client lifecycle via FastAPI lifespan

### Files to Review Before Starting
- `docs/solutions/test-failures/temporary-directory-context-scope.md`
- `docs/solutions/code-organization/monolithic-module-refactor.md`
- `src/safe_journalist/client.py`
- `src/safe_journalist/session.py`

**Ready to implement! Good luck! 🚀**
