# Code Review: FastAPI Text Storage API

## Summary
Implementation is **mostly correct** with clean separation of concerns. Found one critical bug in tests that will cause failures.

---

## ✅ Plan Compliance

All plan requirements implemented:
- ✓ FastAPI app at `src/safe_journalist/api.py` with `/entries` endpoint
- ✓ Storage helper at `src/safe_journalist/storage.py`
- ✓ FastAPI (0.115.0) and uvicorn (0.30.0) added to `pyproject.toml`
- ✓ README updated with run instructions and example curl command
- ✓ Test file `tests/test_api.py` with coverage for valid/invalid inputs
- ✓ App re-exported from `__init__.py`

---

## 🐛 Bugs Found

### Critical: Test Scope Bug (lines 37, 47 in test_api.py)

```39:47:tests/test_api.py
    def test_empty_text_returns_4xx(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                with TestClient(app) as client:
                    response = client.post("/entries", json={"text": ""})

        self.assertGreaterEqual(response.status_code, 400)
        self.assertLess(response.status_code, 500)
        self.assertEqual(list(Path(tmpdir).glob("*")), [])
```

**Issue**: `tmpdir` is accessed outside the `with TemporaryDirectory()` context. The directory no longer exists when the assertions run, causing the test to fail.

**Impact**: Both `test_missing_text_returns_4xx` and `test_empty_text_returns_4xx` will fail.

**Fix**: Move the file check assertion inside the context manager or cache the glob results before the context exits.

---

## ⚠️ Minor Observations

### 1. Validation Logic
The validation in `api.py:29` checks both `not payload.text` and `not payload.text.strip()`:

```29:30:src/safe_journalist/api.py
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="text must be a non-empty string")
```

**Observation**: This correctly handles empty strings and whitespace-only strings. However, Pydantic's `str` type already ensures `text` exists (won't be `None` for non-optional field), so `not payload.text` only catches empty strings. The logic is correct but slightly redundant.

### 2. Path Return Type
The `path` field in `TextEntryOut` returns `str(path)` (line 38), converting `Path` to string.

**Observation**: This is good - ensures JSON serialization works. Just noting that the storage function returns `Path` while the API returns string representation.

---

## 👍 What's Done Well

1. **Clean separation**: Storage logic isolated from API logic
2. **Testable design**: Timestamp injection via mocking, configurable `DATA_DIR` via env var
3. **Type hints**: Full type annotations throughout
4. **Error handling**: Proper 400 response for invalid input
5. **UTC timestamps**: Correct timezone-aware timestamp generation
6. **File safety**: UTF-8 encoding explicitly set, directory creation with `parents=True, exist_ok=True`

---

## 📊 Code Size & Organization

- `api.py`: 39 lines - appropriate size ✓
- `storage.py`: 17 lines - minimal and focused ✓
- `test_api.py`: 48 lines - adequate coverage ✓

No over-engineering detected. File sizes are healthy.

---

## 🎨 Style Consistency

- Consistent use of `from __future__ import annotations`
- Type hints match codebase style (e.g., `-> None`, `-> str`)
- Pydantic models follow standard naming (`In`/`Out` suffix)
- Imports properly organized (stdlib → third-party → local)

---

## 📋 Test Coverage Assessment

Plan requirements vs. implementation:
- ✓ POST valid JSON writes file to correct path
- ✓ File contents match request body
- ✓ Empty text returns 4xx (logic works, but assertion fails due to scope bug)
- ✓ Missing text returns 4xx (logic works, but assertion fails due to scope bug)

**Gap**: No test for whitespace-only input (e.g., `{"text": "   "}`), though the API correctly rejects it.

---

## 🔍 Data Alignment Check

No data format mismatches found:
- Request expects `text: str` ✓
- Response returns `path: str` and `timestamp: str` ✓
- All snake_case (Python convention) ✓
- No nested object confusion ✓

---

## Recommendations

1. **Fix test scope bug immediately** (blocks test suite)
2. Consider adding test for whitespace-only input
3. Optional: Add integration test that doesn't mock `generate_timestamp()` to verify real timestamp format

---

## Verdict

**Implementation quality**: 8/10
- Plan followed correctly
- Clean, maintainable code
- One critical test bug that needs immediate fix
