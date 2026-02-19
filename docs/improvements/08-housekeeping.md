# 08: Code Quality and Housekeeping

**Impact:** Low (correctness/maintainability, not user-facing).
**Effort:** Small
**Files:** various

## Issues and Fixes

### 1. Duplicated STATE_FILE constant

`STATE_FILE = "/tmp/pippin_last_bundle_id"` is defined in both:
- `pippin/commands/system.py:6`
- `pippin/commands/verification.py:7`

And it's also read inline in `pippin/commands/vision.py:35-42`.

**Fix:** Move to a shared location:

```python
# pippin/utils/state.py
import os

STATE_FILE = "/tmp/pippin_last_bundle_id"

def get_last_bundle_id() -> str | None:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return f.read().strip() or None
        except IOError:
            return None
    return None

def set_last_bundle_id(bundle_id: str):
    try:
        with open(STATE_FILE, "w") as f:
            f.write(bundle_id)
    except IOError:
        pass
```

Then replace all the duplicated read/write blocks across `system.py`, `verification.py`, and `vision.py` with calls to `get_last_bundle_id()` / `set_last_bundle_id()`.

### 2. scroll_cmd fetches entire UI tree just for screen dimensions

`interaction.py:46-63` calls `get_ui_tree()` on every scroll just to find the Window frame for dimension calculations. This is an expensive `idb ui describe-all` call.

**Fix options:**
- Cache device dimensions after first lookup (screen size doesn't change).
- Use `xcrun simctl io booted enumerate` or parse device type from `simctl list` to get dimensions without querying the UI tree.
- Hardcode common device sizes as a fallback table (the current 375x812 fallback is already doing this implicitly for one device).

### 3. execute_command capture_output inconsistency

`executor.py:21` defaults `capture_output=True`, but then line 55-56:

```python
capture_output=capture_output,
```

When `capture_output=False`, `result.stdout` is `None`, and the `.strip()` on line 58 will crash. The code should handle this:

```python
if capture_output:
    return result.stdout.strip() if result.stdout else ""
return ""
```

This is technically already handled since `capture_output` defaults to `True`, but the function signature implies `False` is supported.

### 4. Bare except clauses

`system.py:47` has a bare `except:`:
```python
try:
    cmd.extend(shlex.split(args))
except:
    cmd.append(args)
```

**Fix:** Catch `ValueError` specifically (which is what `shlex.split` raises on malformed input).

### 5. Missing `__all__` exports

None of the modules define `__all__`. Not critical but helps with IDE support and prevents accidentally importing internal helpers.

### 6. No type hints on public functions

The command functions have inconsistent type annotations. `vision.py` has some, `system.py` has some, `interaction.py` has none on `scroll_cmd` and `gesture_cmd`.

**Fix:** Add type hints to all public command functions. Keep it simple — just parameter and return types.

### 7. Tests use unittest but could use pytest

The test file uses `unittest.TestCase`. If pytest is already a dependency (or could be added), the tests would be more readable with plain `assert` statements and pytest fixtures for mock setup/teardown.

This is a style preference, not a bug — skip if you prefer unittest.

## Suggested Order

1. Extract `STATE_FILE` to shared module (quick, eliminates duplication)
2. Fix bare except (one-liner)
3. Fix `execute_command` edge case (one-liner)
4. Cache screen dimensions in scroll_cmd (small optimization)
5. Type hints / `__all__` (do alongside other changes, not as a standalone pass)
