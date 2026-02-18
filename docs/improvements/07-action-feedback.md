# 07: Action Feedback Loop

**Impact:** Medium — eliminates the mandatory inspect-after-every-action pattern.
**Effort:** Small
**Files:** `sid/commands/interaction.py`, `sid/main.py`

## Problem

The typical AI agent loop with sid looks like:

```
sid tap "Settings"       → "Tapped at 187, 340"
sid inspect              → { ... new screen ... }
sid tap "General"        → "Tapped at 187, 540"
sid inspect              → { ... new screen ... }
```

Every action requires a follow-up `inspect` to see what happened. That's 2x the calls needed.

## Proposed Changes

### 1. Global `--inspect` flag

Add a global flag that appends an `inspect` result after any interaction command:

```
sid tap "Settings" --inspect
```

Output:
```json
{
  "action": { "status": "ok", "type": "tap", "target": "187,340" },
  "ui": {
    "app": "com.apple.Preferences",
    "screen_id": "Settings",
    "elements": [ ... ]
  }
}
```

One call instead of two. The AI gets immediate feedback on what changed.

### 2. Implementation

In `main.py`, after dispatching to the command handler:

```python
# Add global --inspect flag
parser.add_argument(
    "--inspect",
    action="store_true",
    help="After executing the command, append an inspect of the resulting UI state.",
)

# ... after command dispatch:
if args.inspect and args.command in ["tap", "type", "scroll", "gesture", "launch", "relaunch", "open"]:
    import time
    time.sleep(0.3)  # Brief pause for UI to settle
    inspect_cmd(interactive_only=True)
```

A cleaner approach would be to have each command function return a result dict, then wrap it:

```python
def tap_cmd(query=None, x=None, y=None) -> dict:
    # ... existing logic ...
    return {"status": "ok", "action": "tap", "target": f"{target_x},{target_y}"}
```

Then in `main.py`:

```python
result = tap_cmd(...)
if args.inspect:
    time.sleep(0.3)
    ui_state = get_inspect_result(interactive_only=True)
    combined = {"action": result, "ui": ui_state}
    print(json.dumps(combined, indent=2))
else:
    print(json.dumps(result))
```

### 3. Settle delay

UI transitions take time. The `--inspect` should include a configurable settle delay:

```
sid tap "Settings" --inspect --settle 0.5    # Wait 500ms before inspecting
```

Default: 300ms. This avoids capturing mid-animation states.

### 4. Consider `--wait` integration

Combine with the wait command for transitions:

```
sid tap "Settings" --wait "General" --inspect
```

This means: tap Settings, wait until "General" appears in the UI, then return the inspect result. Useful for navigation transitions where the AI knows what to expect on the next screen.

## What NOT to do

- Don't make `--inspect` the default. It adds latency and token cost to every command. The agent should opt in when it needs feedback.
- Don't capture screenshots automatically — that's a separate concern (`--screenshot` flag if needed).

## Testing

- Test that `--inspect` returns valid combined JSON.
- Test that the action result is included alongside the UI state.
- Test settle delay timing (mock `time.sleep`).
- Test that `--inspect` is ignored for non-interaction commands like `assert` or `logs`.
