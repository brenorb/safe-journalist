# Pre-Implementation Check: Feature 0006 - Configurable Prompt Templates

**Target Components:** `summarizer.py`, `pyproject.toml`, new `templates/` directory  
**Date:** 2026-01-18

---

## ⚠️ Component Risk Assessment

### HIGH SEVERITY
✓ None found

### MEDIUM SEVERITY
✓ None found in target components

### LOW SEVERITY
- **COSE Array Validation** (attestation.py - unrelated component)
  - See: `docs/solutions/.index` Known Issues
  - Status: Documented, not blocking this feature

### KNOWN ISSUES IN RELATED AREAS

**File System Path Issues** (relevant to template loading):
- See: `docs/solutions/configuration-issues/missing-data-dir-json-parse-error.md`
- **Key lesson**: File path errors can fail silently or late (not at startup)
- **Application to this feature**: Template loading should fail fast at module import time, not when summarization is triggered
- **Prevention**: Validate template files exist at module load, raise clear errors if missing

---

## 📚 Related Patterns (2 found)

### 1. Module Organization Pattern
→ `docs/solutions/code-organization/monolithic-module-refactor.md`

**Relevant lessons:**
- Keep modules focused on single responsibility (✓ templates are config, separate from logic)
- Module-level initialization for shared resources (matches plan's module-level template loading)
- Clear error messages for missing dependencies

**Application**: Template loading functions should be clean, focused utilities separate from summarization logic.

### 2. Configuration Management Pattern
→ `docs/solutions/configuration-issues/missing-data-dir-json-parse-error.md`

**Relevant lessons:**
- **Critical**: Configuration errors that fail late are expensive to debug
- Default fallbacks to missing files cause cryptic downstream errors
- Startup validation catches config issues before they propagate
- Clear error messages with actionable fix suggestions

**Application**: 
- Template loading MUST fail fast at module import (not when generate_summary() is called)
- Error message should suggest: "Ensure templates/ directory is packaged correctly. For development, check src/safe_journalist/templates/ exists."
- Consider optional fallback to inline prompts for development ergonomics

---

## ✅ Prevention Strategies

### From Past Solutions

#### 1. Fail Fast at Startup (from missing-data-dir solution)
```python
# summarizer.py - module level
try:
    SUMMARY_INSTRUCTIONS = load_template("summary_instructions.txt")
    CONTEXT_TEMPLATES = parse_context_template(load_template("summary_context.txt"))
except FileNotFoundError as e:
    print(f"ERROR: Template file missing: {e}", file=sys.stderr)
    print("Ensure templates/ directory is packaged correctly", file=sys.stderr)
    # Option A: sys.exit(1) - fail hard
    # Option B: Fall back to inline prompts (better for dev)
    raise
```

**Why**: Prevents silent failures when templates are missing, especially after package installation.

#### 2. Clear Error Messages (from both solutions)
- Point to solution: "Check src/safe_journalist/templates/ exists" or "Reinstall package"
- Include file path in error: `f"Template not found: {expected_path}"`
- Suggest next steps: "For development: ensure templates/ copied. For production: reinstall package."

#### 3. Module-Level Caching (from module-refactor pattern)
```python
# Load once at import time, not on every generate_summary() call
SUMMARY_INSTRUCTIONS = load_template("summary_instructions.txt")
CONTEXT_TEMPLATES = parse_context_template(load_template("summary_context.txt"))
```

**Why**: Performance (avoid repeated file I/O) + fail-fast behavior.

#### 4. Test Isolation Awareness (from test-failures solution)
When writing tests for template loading:
- ✓ Ensure test fixtures for template files are properly scoped
- ✓ Don't rely on global state that might be cleared
- ✓ Mock file loading at the right layer (use `patch.object` on load_template, not Path)

### From Component Tag Analysis
- Tag `python`: 2 solutions - follow established Python patterns
- Tag `refactoring`: 1 solution - maintain clean separation of concerns
- Tag `configuration`: 1 solution - validate early, fail clearly

---

## 🔗 Dependency & Risk Analysis

### Components You'll Touch

**summarizer.py**
- Status: ✓ No known issues
- Current state: Hardcoded prompts in lines 46-60
- Risk level: LOW (pure refactor, no algorithm changes)

**pyproject.toml**
- Status: ✓ No known issues
- Current state: Uses `uv_build` backend (not setuptools)
- Risk level: MEDIUM - Package data syntax differs between build backends
- **Action required**: Research `uv_build` package data syntax (may differ from setuptools)

**New: templates/ directory**
- Risk level: MEDIUM - Resource loading varies between development and installed package
- **Considerations:**
  - Dev: `Path(__file__).parent / "templates"` works ✓
  - Installed package: Need to verify templates are included in distribution
  - Alternative: Use `importlib.resources` for more robust cross-environment loading

### Package Data Configuration Uncertainty

**Current state**: No existing package data configuration in `pyproject.toml`  
**Build backend**: `uv_build>=0.9.24` (not setuptools)

**Research needed:**
1. Does `uv_build` automatically include package directories? (likely YES)
2. Does it respect `[tool.setuptools.package-data]` syntax? (probably NO - that's setuptools-specific)
3. Should we use `importlib.resources` or `Path(__file__)`?

**Recommendation**: 
- Start with `Path(__file__).parent / "templates" / filename` (simple, works in dev)
- Test after installation: `uv pip install -e .` and verify templates accessible
- If templates not included, research uv-specific syntax or add manifest file

---

## 💡 Recommendations

### 1. Critical: Validate Package Data Inclusion

**Before writing code**, test uv's package data behavior:

```bash
# Create dummy test
mkdir -p src/safe_journalist/test_resources
echo "test" > src/safe_journalist/test_resources/dummy.txt

# Install package
uv pip install -e .

# Check if resource accessible
uv run python -c "from pathlib import Path; import safe_journalist; print((Path(safe_journalist.__file__).parent / 'test_resources' / 'dummy.txt').exists())"
```

If False → need explicit configuration or use `importlib.resources`.

### 2. Implement Fail-Fast Behavior

Load templates at module level with clear error handling:

```python
# summarizer.py - at top of file after imports
import sys

try:
    SUMMARY_INSTRUCTIONS = load_template("summary_instructions.txt")
    CONTEXT_TEMPLATES = parse_context_template(load_template("summary_context.txt"))
except FileNotFoundError as e:
    template_dir = Path(__file__).parent / "templates"
    print(f"ERROR: Summarization template not found: {e}", file=sys.stderr)
    print(f"Expected directory: {template_dir}", file=sys.stderr)
    print("Ensure templates are packaged correctly or reinstall package.", file=sys.stderr)
    # Option: Fall back to inline prompts for graceful degradation
    raise
```

### 3. Add Development Fallback (Optional)

For better dev experience, consider fallback to inline prompts if templates missing:

```python
# summarizer.py
INLINE_FALLBACK = {
    "instructions": "Generate a concise 3-5 bullet summary...",
    "WITH_PREVIOUS_SUMMARY": "Previous summary:\n{summary_content}\n\nNew notes:\n{entries_text}\n\n",
    "NO_PREVIOUS_SUMMARY": "Notes from journalist:\n{entries_text}\n\n"
}

try:
    SUMMARY_INSTRUCTIONS = load_template("summary_instructions.txt")
    CONTEXT_TEMPLATES = parse_context_template(load_template("summary_context.txt"))
    print("✓ Loaded prompt templates from templates/")
except FileNotFoundError:
    print("⚠ Template files not found, using inline fallback prompts", file=sys.stderr)
    SUMMARY_INSTRUCTIONS = INLINE_FALLBACK["instructions"]
    CONTEXT_TEMPLATES = {k: v for k, v in INLINE_FALLBACK.items() if k != "instructions"}
```

**Trade-off**: More resilient in dev, but masks packaging issues. Only use if clearly logged.

### 4. Consider importlib.resources

For maximum compatibility (especially in zip-imported packages):

```python
try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # Python <3.9 backport

def load_template(filename: str) -> str:
    """Load template from package resources."""
    template_file = files("safe_journalist") / "templates" / filename
    return template_file.read_text(encoding="utf-8")
```

**Why**: Works correctly in:
- Development (source tree)
- Installed package (site-packages)
- Zipped eggs/wheels
- Frozen applications (PyInstaller, etc.)

**Trade-off**: Slightly more complex, but more robust.

### 5. Test Strategy

Before marking complete:

```bash
# Test 1: Dev environment (current)
uv run python -c "from safe_journalist import summarizer; print('Dev OK')"

# Test 2: Editable install
uv pip install -e .
uv run python -c "from safe_journalist import summarizer; print('Editable install OK')"

# Test 3: Full install (clean environment)
uv pip uninstall safe-journalist
uv pip install .
uv run python -c "from safe_journalist import summarizer; print('Full install OK')"

# Test 4: Verify existing tests still pass
uv run pytest tests/test_summarizer.py -v
```

---

## 🚀 Ready to Implement?

### Pre-flight Checklist

- [ ] Read `docs/solutions/configuration-issues/missing-data-dir-json-parse-error.md` for file path error patterns
- [ ] Test uv package data behavior (see Recommendation #1)
- [ ] Decide: `Path(__file__)` vs `importlib.resources` based on testing
- [ ] Plan fail-fast error handling at module level
- [ ] Plan test for both dev and installed package scenarios

### Edge Cases to Consider

1. **Missing template file** → Caught at module load, clear error
2. **Malformed template format** → `parse_context_template()` should validate section markers
3. **Missing template variables** → `.format()` will raise KeyError, catch and wrap with context
4. **Template encoding issues** → Always use `encoding="utf-8"` when reading
5. **Package not installed correctly** → Test in clean venv

### Success Criteria

- [ ] Templates loaded at module level (not per-call)
- [ ] Clear error if templates missing
- [ ] Templates accessible in both dev and installed package
- [ ] Existing tests pass unchanged
- [ ] Generated prompts match previous behavior exactly
- [ ] Easy for users to customize (just edit .txt files)

---

## 📋 Implementation Notes

**Estimated complexity**: LOW-MEDIUM (refactor, no new functionality)  
**Estimated time**: 30-60 minutes (including testing)  
**Risk level**: LOW (pure refactor with comprehensive tests available)

**Proceed when ready!** The risks are well-understood and mitigatable.
