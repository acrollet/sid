# 04: Consistent Exit Codes and Error Model

**Impact:** High — AI agents rely on exit codes to know if a command succeeded.
**Effort:** Small
**Files:** all command files, `sid/utils/errors.py` (new)

## Problem

Exit code behavior is inconsistent across commands:

| Command | On failure | Exit code |
|---------|-----------|-----------|
| `assert` | Prints `FAIL: ...` | `sys.exit(1)` |
| `wait` | Prints `FAIL: ERR_TIMEOUT: ...` | `sys.exit(1)` |
| `tap` (element not found) | Prints to stderr | `0` (success!) |
| `tap` (no args) | Prints to stderr | `0` |
| `inspect` (idb error) | Prints error to stderr, then empty JSON to stdout | `0` |
| `logs` (no target app) | Prints to stderr | `0` |
| `launch` (error) | Prints to stderr | `0` |

An AI agent running `sid tap "Nonexistent"` gets exit code 0 and thinks it succeeded.

## Proposed Error Model

### 1. Define error codes in `sid/utils/errors.py`

```python
import sys

# Exit codes
EXIT_SUCCESS = 0
EXIT_ELEMENT_NOT_FOUND = 1
EXIT_TIMEOUT = 2
EXIT_APP_NOT_RUNNING = 3
EXIT_COMMAND_FAILED = 4
EXIT_INVALID_ARGS = 5

# Structured error prefixes (for stderr)
ERR_ELEMENT_NOT_FOUND = "ERR_ELEMENT_NOT_FOUND"
ERR_COORDINATES_NOT_FOUND = "ERR_COORDINATES_NOT_FOUND"
ERR_TIMEOUT = "ERR_TIMEOUT"
ERR_NO_TARGET_APP = "ERR_NO_TARGET_APP"
ERR_APP_CRASHED = "ERR_APP_CRASHED"
ERR_TEXT_MISMATCH = "ERR_TEXT_MISMATCH"
ERR_COMMAND_FAILED = "ERR_COMMAND_FAILED"

def fail(error_code: str, message: str, exit_code: int = EXIT_COMMAND_FAILED):
    """Print structured error to stderr and exit with appropriate code."""
    print(f"FAIL: {error_code}: {message}", file=sys.stderr)
    sys.exit(exit_code)
```

### 2. Rules for all commands

- **Success:** Print result to stdout, exit 0.
- **Failure:** Print `FAIL: ERR_CODE: message` to stderr, exit non-zero.
- **Warnings:** Print `WARN: message` to stderr, still exit 0 (the command succeeded, but something is off).

### 3. Apply to each command

**`tap_cmd`** — currently silent on failure:
```python
# Before (exits 0 on failure):
print(f"ERR_ELEMENT_NOT_FOUND: Element '{query}' not found.", file=sys.stderr)

# After:
fail(ERR_ELEMENT_NOT_FOUND, f"Element '{query}' not found.", EXIT_ELEMENT_NOT_FOUND)
```

**`inspect_cmd`** — currently returns empty JSON on error:
```python
# Before:
except Exception as e:
    print(f"Error inspecting UI: {e}", file=sys.stderr)
    # Falls through, prints nothing useful to stdout

# After:
except Exception as e:
    fail(ERR_COMMAND_FAILED, f"Could not inspect UI: {e}")
```

**`launch_cmd`**, **`stop_cmd`**, etc. — same pattern.

### 4. Structured output on success too

For commands that mutate state, output a brief JSON confirmation to stdout so the AI can parse it:

```python
# tap_cmd success:
print(json.dumps({"status": "ok", "action": "tap", "target": f"{target_x},{target_y}"}))

# launch_cmd success:
print(json.dumps({"status": "ok", "action": "launch", "bundle_id": bundle_id}))
```

This is optional but helps agents that parse stdout programmatically rather than checking exit codes.

## Testing

- For every command, add a test case for the failure path that asserts a non-zero exit code.
- Test that stderr contains the structured `FAIL: ERR_*:` prefix.
- Test that stdout is clean (no error text mixed into JSON output).
