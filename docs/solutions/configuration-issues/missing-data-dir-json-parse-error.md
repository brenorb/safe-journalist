---
title: "Missing DATA_DIR Causes JSON Parse Error in Frontend"
date: 2026-01-18
category: configuration-issues
severity: high
tags:
  - environment-variables
  - fastapi
  - frontend-errors
  - configuration
  - dotenv
components:
  - src/safe_journalist/api.py
  - static/app.js
  - .env
status: resolved
related_issues: []
---

# Missing DATA_DIR Environment Variable Causes Misleading JSON Parse Error

## Problem Symptom

**Frontend Error:**
```
✗ Error: Unexpected token 'I', "Internal S"... is not valid JSON
```

**User Experience:**
- User submits entry via web UI
- Green "Entry submitted successfully!" message appears briefly
- But entry doesn't show in "Recent Entries" list
- Status doesn't update

**Server Logs:**
```
INFO:     127.0.0.1:61074 - "POST /entries HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
...
OSError: [Errno 30] Read-only file system: '/data'
```

## Why This Error is Misleading

The error message **"...is not valid JSON"** suggests a frontend or API response issue, but the actual problem is:

1. Backend tries to write to `/data` (read-only system directory)
2. FastAPI catches the unhandled `OSError` exception
3. FastAPI returns 500 Internal Server Error as **HTML/plain text** (not JSON)
4. Frontend's `response.json()` tries to parse HTML error page
5. JSON parser fails with cryptic "Unexpected token" error

The chain: **Missing env var → File system error → HTML error page → JSON parse error**

## Investigation Steps

### What We Tried First

1. **Checked frontend JavaScript** ✗
   - API integration code was correct
   - Error handling properly implemented

2. **Verified API endpoint logic** ✗
   - POST `/entries` endpoint implementation was correct
   - Storage functions working in tests

3. **Examined browser console** ✓
   - Found the JSON parse error
   - Status code was 500 (not 400/404)

### Root Cause Discovery

Checked server terminal logs and found:

```python
File "/Users/breno/Documents/code/PROJECTS/hackathon/safe-journalist/src/safe_journalist/storage.py", line 22, in write_entry
    entries_dir.mkdir(parents=True, exist_ok=True)
...
OSError: [Errno 30] Read-only file system: '/data'
```

**Root cause**: `DATA_DIR` environment variable not set, defaulting to `/data` (system root directory, read-only without sudo).

## Root Cause Analysis

### Technical Explanation

```python
# api.py:36-37
def get_data_dir() -> str:
    return os.getenv("DATA_DIR", "/data")  # ← Defaults to /data if not set
```

On macOS/Linux, `/data` is typically:
- Owned by root
- Read-only for regular users
- Not suitable for application data

### Why It Happens

1. Application starts without `.env` file loaded
2. `get_data_dir()` returns default `/data`
3. First entry creation attempts `mkdir("/data/entries")`
4. OS raises `OSError: Read-only file system`
5. FastAPI's default error handler catches it
6. Returns 500 with HTML error page instead of JSON

### Why It's Subtle

- ✅ Server starts successfully (no errors at startup)
- ✅ GET requests work (status, alert, entries list all succeed)
- ❌ Only fails on first POST that tries to write files
- ❌ Error message points to wrong layer (JSON parsing vs configuration)

## Working Solution

### 1. Create `.env` File

```bash
cat > .env << 'EOF'
# Safe Journalist Configuration
DATA_DIR=/Users/breno/Documents/code/PROJECTS/hackathon/safe-journalist/data

# Maple AI (optional - only for summarization)
# MAPLE_API_KEY=your-key-here

# Summarization triggers
SUMMARY_TRIGGER_COUNT=3
SUMMARY_TRIGGER_DELAY=10
EOF
```

**Important**: Use absolute path or project-relative path, NOT `/data`.

### 2. Verify `.env` is Loaded

The code already has `load_dotenv()`:

```python
# api.py:6,16
from dotenv import load_dotenv
...
load_dotenv()
```

### 3. Restart Server

```bash
# Server will now load .env automatically
uv run uvicorn safe_journalist.api:app --reload --port 8000
```

### 4. Verify It Works

```bash
# Check data directory was created
ls -la /Users/breno/Documents/code/PROJECTS/hackathon/safe-journalist/data/

# Should show:
# drwxr-xr-x  entries/
# drwxr-xr-x  summaries/
```

## Alternative Solutions

### Option 1: Export Environment Variable (Temporary)

```bash
export DATA_DIR=/Users/breno/Documents/code/PROJECTS/hackathon/safe-journalist/data
uv run uvicorn safe_journalist.api:app --reload --port 8000
```

**Downside**: Lost on terminal close, must re-export each session.

### Option 2: Inline Environment Variable

```bash
DATA_DIR=/Users/breno/Documents/code/PROJECTS/hackathon/safe-journalist/data \
  uv run uvicorn safe_journalist.api:app --reload --port 8000
```

**Downside**: Verbose, easy to forget.

### Option 3: Change Default in Code (Not Recommended)

```python
# api.py
def get_data_dir() -> str:
    return os.getenv("DATA_DIR", "./data")  # Changed default
```

**Downside**: Hardcodes assumption, makes deployment harder.

## Prevention Strategies

### 1. Add Startup Validation

**File**: `src/safe_journalist/api.py`

```python
import sys
from pathlib import Path

@app.on_event("startup")
async def validate_config():
    """Validate critical environment variables on startup"""
    data_dir = Path(get_data_dir())
    
    # Check if directory is writable
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        test_file = data_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except (OSError, PermissionError) as e:
        print(f"ERROR: DATA_DIR '{data_dir}' is not writable: {e}", file=sys.stderr)
        print("Please set DATA_DIR environment variable to a writable directory", file=sys.stderr)
        sys.exit(1)
    
    print(f"✓ DATA_DIR configured: {data_dir}")
```

**Benefits**:
- Fails fast at startup (not on first write)
- Clear error message pointing to solution
- Prevents misleading downstream errors

### 2. Update README.md

Add prominent configuration section:

```markdown
## Configuration

Create a `.env` file in the project root:

\`\`\`bash
# Required
DATA_DIR=/path/to/data/directory

# Optional (for AI summarization)
MAPLE_API_KEY=your-key
SUMMARY_TRIGGER_COUNT=3
SUMMARY_TRIGGER_DELAY=10
\`\`\`

**Important**: `DATA_DIR` must be an absolute path to a writable directory.

### Quick Start

\`\`\`bash
# Create .env
echo "DATA_DIR=$PWD/data" > .env

# Start server
uv run uvicorn safe_journalist.api:app --reload
\`\`\`
```

### 3. Add Example .env File

**File**: `.env.example`

```bash
# Safe Journalist Configuration Example
# Copy this file to .env and update values

# Data directory for entries and summaries (REQUIRED)
# Use absolute path or $PWD/data for project directory
DATA_DIR=/path/to/your/data/directory

# Maple AI Configuration (optional - only needed for AI summarization)
MAPLE_API_URL=https://enclave.trymaple.ai
MAPLE_API_KEY=your-api-key-here
MAPLE_MODEL=llama-3.3-70b

# Summarization triggers
SUMMARY_TRIGGER_COUNT=3
SUMMARY_TRIGGER_DELAY=10
```

### 4. Better Error Handling in Frontend

**File**: `static/app.js`

```javascript
// app.js - Enhanced error handling
async function submitEntry(text) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';
    
    try {
        const response = await fetch('/entries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        
        // Check if response is actually JSON before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Server returned non-JSON response. Check server logs.');
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to submit entry');
        }
        
        const data = await response.json();
        showMessage(entryMessage, '✓ Entry submitted successfully!', 'success');
        // ... rest of success handling
        
    } catch (error) {
        // More helpful error message
        if (error.message.includes('non-JSON')) {
            showMessage(entryMessage, 
                '✗ Server error (check terminal logs). Possible configuration issue.', 
                'error'
            );
        } else {
            showMessage(entryMessage, `✗ Error: ${error.message}`, 'error');
        }
        throw error;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Entry';
    }
}
```

## Impact Assessment

**Affected Operations:**
- Any POST `/entries` request
- Background summarization jobs (write summaries)
- Any file write operation in storage layer

**Severity: High**
- Blocks core functionality (can't create entries)
- Misleading error message delays diagnosis
- Silent failure (appears to work briefly before error)

**Blast Radius:**
- User-facing: Complete entry creation failure
- Backend: All file write operations fail
- No data corruption (fails before any writes)

## Verification

### Before Fix

```bash
$ curl -X POST http://localhost:8000/entries \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'

# Returns HTML error page instead of JSON
<!DOCTYPE html>
<html>
  <head><title>500 Internal Server Error</title></head>
  <body>...</body>
</html>
```

### After Fix

```bash
$ curl -X POST http://localhost:8000/entries \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'

# Returns JSON success response
{
  "path": "/Users/breno/Documents/code/PROJECTS/hackathon/safe-journalist/data/entries/20260118T030206Z-entry.md",
  "timestamp": "20260118T030206Z"
}
```

### File System Check

```bash
$ ls -la data/
drwxr-xr-x  entries/
drwxr-xr-x  summaries/

$ cat data/entries/20260118T030206Z-entry.md
test
```

## Related Documentation

- [FastAPI Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [python-dotenv Documentation](https://github.com/theskumar/python-dotenv)
- [Environment Variables Best Practices](https://12factor.net/config)

## Tags for Future Search

`environment-variables` `configuration` `fastapi` `json-parse-error` `misleading-error` `startup-validation` `dotenv` `file-permissions` `read-only-filesystem`

## Lessons Learned

1. **Misleading errors are expensive** - JSON parse error hid the real issue (configuration)
2. **Fail fast at startup** - Validate critical config before accepting requests
3. **Explicit is better than implicit** - Don't rely on environment variable defaults
4. **Error messages should guide users** - "Server error (check logs)" beats "Invalid JSON"
5. **Document configuration prominently** - Setup steps should be in README, not buried in code

## Future Improvements

1. **Add startup validation** to catch configuration errors early
2. **Create `.env.example`** so users know what to configure
3. **Improve frontend error handling** to detect non-JSON responses
4. **Add health check endpoint** (`/health`) that validates configuration
5. **Consider configuration file** (e.g., `config.yaml`) for complex setups
