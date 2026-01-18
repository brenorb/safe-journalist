# TDD Methodology Guide

This project uses Test-Driven Development for all feature implementations.

---

## The TDD Cycle

```
┌──────────┐      ┌──────────┐      ┌──────────┐
│   RED    │ ───> │  GREEN   │ ───> │ REFACTOR │
└──────────┘      └──────────┘      └──────────┘
     │                  │                  │
 Write Tests     Implement Code      Clean Code
 (They Fail)     (Tests Pass)    (Tests Still Pass)
```

**Golden Rule:** Never write production code without a failing test first.

---

## Quick Recipe

```python
while feature_not_complete:
    # 1. RED - Write a failing test
    write_test_for_next_behavior()
    run_tests()  # Should fail ❌
    
    # 2. GREEN - Make it pass (simplest way)
    write_minimal_code_to_pass_test()
    run_tests()  # Should pass ✅
    
    # 3. REFACTOR - Clean up (optional)
    if code_is_messy:
        refactor_while_keeping_tests_green()
        run_tests()  # Should still pass ✅
```

---

## Implementation Pattern

### 1. Start with Storage/Data Layer
- Write tests for data operations first
- Mock external dependencies
- Test edge cases (empty, None, etc.)

### 2. Build Business Logic
- Test with mocked storage
- Test happy path + error cases
- Verify correct behavior, not implementation

### 3. Wire up API/Interface
- Integration tests with real components
- Test triggers and side effects
- Verify non-blocking behavior

---

## Best Practices

### Test Naming
```python
# ✅ Good - describes behavior
def test_third_entry_triggers_summarization(self):

# ❌ Bad - describes implementation
def test_count_equals_three(self):
```

### Test Structure (AAA Pattern)
```python
def test_something(self):
    # Arrange - setup
    data = create_test_data()
    
    # Act - execute
    result = function_under_test(data)
    
    # Assert - verify
    self.assertEqual(result, expected)
```

### Mocking Strategy
```python
# Mock external dependencies
with patch("module.external_api_call") as mock_api:
    mock_api.return_value = {"status": "success"}
    result = my_function()
    mock_api.assert_called_once()
```

### Test Isolation
- Each test should be independent
- Use `setUp()` / `tearDown()` or context managers
- Don't rely on test execution order

---

## Common Pitfalls

❌ **Writing tests after code** - You'll write tests that pass, not that drive design  
❌ **Testing implementation** - Test behavior, not internal details  
❌ **Skipping edge cases** - Empty lists, None values, errors matter  
❌ **Large test increments** - Small steps = easier debugging  
❌ **Not refactoring** - Keep code clean, tests give you confidence  

---

## Running Tests

```bash
# All tests
uv run pytest -v

# Specific module
uv run pytest tests/test_module.py -v

# With coverage
uv run pytest --cov=safe_journalist --cov-report=term

# Watch mode (if using pytest-watch)
uv run ptw
```

---

## Success Criteria

Before considering a feature complete:

- [ ] All tests written before implementation code
- [ ] All tests passing
- [ ] Code coverage > 90% for new code
- [ ] No tests skipped or marked as xfail
- [ ] Tests document expected behavior
- [ ] Refactoring complete (no TODOs, clean code)

---

## Example: Adding a New Feature

```python
# 1. RED - Write test
def test_new_feature_does_something(self):
    result = new_feature("input")
    self.assertEqual(result, "expected")

# Run: pytest -v
# ✗ FAILED - AttributeError: module has no attribute 'new_feature'

# 2. GREEN - Implement
def new_feature(input: str) -> str:
    return "expected"  # Simplest possible solution

# Run: pytest -v  
# ✅ PASSED

# 3. REFACTOR - Improve (if needed)
def new_feature(input: str) -> str:
    # Add proper logic, extract helpers, etc.
    return process(input)

# Run: pytest -v
# ✅ PASSED - Tests still green!
```

---

## Why TDD?

**Benefits we've observed:**
- Zero production bugs (tests catch issues early)
- Fearless refactoring (test suite catches regressions)
- Self-documenting code (tests explain behavior)
- Better design (thinking about interfaces first)
- Faster debugging (test failures pinpoint issues)

**Investment vs Return:**
- Writing tests: 40% of time
- Saved debugging: Countless hours
- Verdict: Worth it

---

## References

- Feature 0003: See `/docs/features/0003_IMPLEMENTATION_SUMMARY.md` for real-world example
- All features in `/docs/features/` should follow this methodology
