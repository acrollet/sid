# 03: Composite Context Command

**Impact:** High — reduces multi-call orientation to a single call.
**Effort:** Medium
**Files:** new `sid/commands/context.py`, `sid/main.py`

## Problem

To understand "where am I and what can I do?", an AI agent currently needs:

1. `sid inspect` — what elements are on screen?
2. `sid screenshot` — what does it look like? (if multimodal)
3. `sid logs` — did anything go wrong?
4. Manual reasoning about which app is running, what screen this is, etc.

That's 2-3 round-trips minimum, each costing latency and tokens. The agent also has to synthesize the results itself, which is error-prone.

## Proposed Command

```
sid context [--include-logs] [--screenshot <path>]
```

Returns a single JSON blob with everything an AI needs to orient:

```json
{
  "device": {
    "udid": "BB13ECAA-05F4-4E3B-A220-235BDBADFAB5",
    "name": "iPhone 16 Pro",
    "runtime": "iOS 18.2",
    "state": "Booted"
  },
  "app": {
    "bundle_id": "com.example.myapp",
    "state": "running"
  },
  "screen": {
    "title": "Settings",
    "breadcrumb": ["Settings", "General", "About"],
    "focused_element": { "id": "name_field", "type": "TextField", "value": "" },
    "alert": null
  },
  "ui": [
    {
      "type": "NavigationBar",
      "label": "About",
      "children": [
        { "type": "Button", "label": "General" }
      ]
    },
    {
      "type": "Table",
      "children": [
        { "type": "Cell", "label": "Name", "value": "John's iPhone" },
        { "type": "Cell", "label": "iOS Version", "value": "18.2" }
      ]
    }
  ],
  "logs": null,
  "screenshot": null
}
```

## Implementation

### `sid/commands/context.py`

```python
def context_cmd(include_logs=False, screenshot_path=None):
    result = {}

    # 1. Device info
    result["device"] = get_device_info()

    # 2. App info (from state file + simctl)
    result["app"] = get_app_info()

    # 3. Screen analysis
    tree = get_ui_tree_hierarchical()
    result["screen"] = analyze_screen(tree)

    # 4. UI hierarchy (using the new hierarchical inspect)
    result["ui"] = [simplify_node(n) for n in tree]

    # 5. Optional logs
    if include_logs:
        result["logs"] = get_recent_logs(lines=20)

    # 6. Optional screenshot
    if screenshot_path:
        take_screenshot(screenshot_path)
        result["screenshot"] = screenshot_path

    print(json.dumps(result, indent=2))
```

### Screen analysis helpers

```python
def analyze_screen(tree):
    """Extract high-level screen context from the UI tree."""
    info = {
        "title": None,
        "breadcrumb": [],
        "focused_element": None,
        "alert": None,
    }

    # Walk tree looking for:
    # - NavigationBar title → screen title, back button label → breadcrumb
    # - Alert/Sheet → surface it prominently
    # - Focused element (text field with keyboard visible, etc.)
    # ... (implementation details)

    return info
```

### `get_device_info()`

```python
def get_device_info():
    """Get info about the booted simulator."""
    output = execute_command(
        ["xcrun", "simctl", "list", "devices", "booted", "--json"],
        capture_output=True
    )
    # Parse JSON, extract device name, runtime, udid
    ...
```

## Key Design Decisions

### Why not just pipe `inspect` output?
The `context` command adds semantic analysis on top of raw UI data. The `screen.breadcrumb` and `screen.alert` fields require walking the tree and understanding iOS UI conventions (NavigationBar structure, Alert detection). This logic shouldn't live in `inspect`.

### What about token cost?
The hierarchical UI tree is more verbose than the flat list. Mitigate with:
- `--depth N` to limit tree depth (default 4 or so)
- `--brief` mode that only returns `screen` + `app` metadata without the full `ui` tree
- Omit empty fields (don't include `"alert": null` etc.)

### Should it replace `inspect`?
No. `inspect` is for targeted UI queries during a flow. `context` is for orientation at the start of a task or after losing track. They serve different purposes.

## CLI Integration

```
sid context                          → full context, no logs, no screenshot
sid context --include-logs           → include last 20 lines of app logs
sid context --screenshot state.png   → also capture a screenshot
sid context --brief                  → just screen metadata, no UI tree
```

## Testing

- Mock `idb ui describe-all` and `xcrun simctl list devices` to test the assembly logic.
- Test breadcrumb extraction with NavigationBar mocks containing Back buttons with various labels.
- Test alert detection with mock Alert nodes.
