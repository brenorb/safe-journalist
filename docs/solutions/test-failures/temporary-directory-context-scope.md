---
title: "TemporaryDirectory Context Manager Scope Bug in Tests"
date: 2026-01-18
category: test-failures
severity: high
tags:
  - python
  - pytest
  - context-managers
  - tempfile
  - fastapi-testing
components:
  - tests/test_api.py
status: resolved
related_issues: []
---

# TemporaryDirectory Context Manager Scope Bug

## Problem Symptom

Test failures with `FileNotFoundError` or directory not existing errors when trying to assert on files that should have been created (or not created) in a temporary directory.

**Observed behavior:**
- Tests pass the actual API logic validation
- Tests fail during assertion phase with path-related errors
- Intermittent failures depending on timing of garbage collection

**Error message (typical):**
```python
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmp_xyz123'
```

## Investigation Steps

### What We Tried First

1. **Checked file creation logic** ✗
   - API file writing code was correct
   - Files were being created during test execution

2. **Verified path construction** ✗
   - Paths were correctly constructed
   - `DATA_DIR` environment variable properly patched

3. **Examined test execution order** ✗
   - Not an order-dependent issue
   - Failed consistently for specific test methods

### Root Cause Discovery

Found that assertions accessing `tmpdir` were **outside** the `with TemporaryDirectory()` context manager scope. Once the context exits, Python automatically deletes the temporary directory, making any subsequent file system operations fail.

**Problematic code pattern:**

```python
def test_empty_text_returns_4xx(self) -> None:
    with TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
            with TestClient(app) as client:
                response = client.post("/entries", json={"text": ""})
    
    # ❌ tmpdir no longer exists here!
    self.assertGreaterEqual(response.status_code, 400)
    self.assertLess(response.status_code, 500)
    self.assertEqual(list(Path(tmpdir).glob("*")), [])  # FAIL: directory deleted
```

## Root Cause Analysis

### Technical Explanation

Python's `TemporaryDirectory()` context manager:
1. Creates a temporary directory on `__enter__`
2. Returns the path as `tmpdir`
3. Automatically deletes the directory and all contents on `__exit__`

The scope issue occurred because:
- The `response` object was created **inside** the context
- But assertions accessing `tmpdir` were **outside** the context
- When the context exited, the directory was deleted
- Assertions tried to access a non-existent path

### Why It's Subtle

This bug is easy to miss because:
- The `response` object survives outside the context (no issue)
- The `tmpdir` string variable is still accessible (it's just a string)
- The actual **directory** no longer exists (filesystem cleaned up)
- Indentation makes the scope less obvious with nested contexts

## Working Solution

### Fix: Move Assertions Inside Context

Keep assertions inside the `TemporaryDirectory()` context but outside the inner contexts:

```python
def test_empty_text_returns_4xx(self) -> None:
    with TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
            with TestClient(app) as client:
                response = client.post("/entries", json={"text": ""})
        
        # ✅ Still inside TemporaryDirectory context
        self.assertGreaterEqual(response.status_code, 400)
        self.assertLess(response.status_code, 500)
        self.assertEqual(list(Path(tmpdir).glob("*")), [])
```

### Alternative: Cache Results Before Exit

If assertions must be outside, cache the directory contents:

```python
def test_empty_text_returns_4xx(self) -> None:
    with TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
            with TestClient(app) as client:
                response = client.post("/entries", json={"text": ""})
        
        files_created = list(Path(tmpdir).glob("*"))  # Cache before exit
    
    # Now safe to check outside context
    self.assertGreaterEqual(response.status_code, 400)
    self.assertLess(response.status_code, 500)
    self.assertEqual(files_created, [])
```

## Impact Assessment

**Affected tests:**
- `test_missing_text_returns_4xx` 
- `test_empty_text_returns_4xx`

**Severity: High**
- Blocks entire test suite from passing
- False negatives (tests fail even when API works correctly)
- Reduces confidence in test coverage

**Blast radius:**
- Limited to test file
- No production impact
- API implementation was correct

## Prevention Strategies

### 1. Visual Scope Inspection

Always verify context manager scope visually:

```python
with TemporaryDirectory() as tmpdir:
    # Code using tmpdir goes here
    pass
# tmpdir is deleted after this line
```

### 2. Linting Rule (Future)

Consider a custom linter rule to detect:
- Variables from `as tmpdir` being accessed outside `with` block
- Common pattern: `with TemporaryDirectory() as X:` ... use of `X` outside

### 3. Test Template Pattern

Create a reusable test fixture:

```python
@contextmanager
def temp_data_dir():
    with TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
            yield tmpdir
        # tmpdir still exists here for cleanup assertions

# Usage
def test_something(self):
    with temp_data_dir() as tmpdir:
        # All test code here
        client = TestClient(app)
        response = client.post(...)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(Path(tmpdir).glob("*")), [])
```

### 4. Pytest Fixtures Alternative

For pytest-style tests (instead of unittest):

```python
@pytest.fixture
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return tmp_path

def test_empty_text_returns_4xx(temp_data_dir):
    client = TestClient(app)
    response = client.post("/entries", json={"text": ""})
    
    assert response.status_code == 400
    assert list(temp_data_dir.glob("*")) == []
    # tmp_path cleanup handled by pytest automatically
```

## Verification

### Test Results Before Fix

```bash
$ uv run --extra dev pytest tests/test_api.py -v
...
tests/test_api.py::TestApi::test_empty_text_returns_4xx FAILED
tests/test_api.py::TestApi::test_missing_text_returns_4xx FAILED
tests/test_api.py::TestApi::test_post_text_writes_file PASSED
```

### Test Results After Fix

```bash
$ uv run --extra dev pytest tests/test_api.py -v
============================= test session starts ==============================
tests/test_api.py::TestApi::test_empty_text_returns_4xx PASSED           [ 33%]
tests/test_api.py::TestApi::test_missing_text_returns_4xx PASSED         [ 66%]
tests/test_api.py::TestApi::test_post_text_writes_file PASSED            [100%]

============================== 3 passed in 0.31s
```

### Live API Verification

Confirmed API behavior is correct:

```bash
# Valid request
$ curl -sS http://127.0.0.1:8000/entries \
  -H "content-type: application/json" \
  -d '{"text":"Test entry"}'
{"path":"/tmp/safe-journalist-data/20260118T014737Z.md","timestamp":"20260118T014737Z"}

# Empty text (correctly rejected)
$ curl -sS http://127.0.0.1:8000/entries \
  -H "content-type: application/json" \
  -d '{"text":""}'
{"detail":"text must be a non-empty string"}
# HTTP Status: 400
```

## Related Documentation

- [Python tempfile docs](https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryDirectory)
- [Context Manager Best Practices](https://docs.python.org/3/library/contextlib.html)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)

## Tags for Future Search

`python` `context-manager` `tempfile` `scope-bug` `test-fixtures` `fastapi-testing` `unittest` `pytest` `temporary-directory` `filesystem-cleanup`

## Lessons Learned

1. **Context managers have strict boundaries** - Variables created in context may outlive the context, but resources (files, connections) do not
2. **Indentation matters** - With nested contexts, carefully track which scope your code is in
3. **Tests can lie** - A failing test doesn't always mean broken implementation; check test correctness first
4. **Filesystem operations are fragile** - Always verify paths exist before asserting on their contents
5. **Design for testability** - Using fixtures/helpers reduces context nesting and scope confusion
