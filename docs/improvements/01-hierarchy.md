# 01: Preserve UI Hierarchy in Inspect Output

**Impact:** Critical — this is the single biggest reason AI agents struggle with Pippin.
**Effort:** Medium
**Files:** `pippin/utils/ui.py`, `pippin/commands/vision.py`

## Problem

`get_ui_tree()` in `ui.py` calls `flatten_tree()` which recursively collapses the entire accessibility tree into a flat list. All parent-child relationships are lost. When an AI sees:

```json
{
  "elements": [
    { "label": "Back", "type": "Button" },
    { "label": "Settings", "type": "StaticText" },
    { "label": "Wi-Fi", "type": "Cell" },
    { "label": "Bluetooth", "type": "Cell" },
    { "label": "General", "type": "Cell" }
  ]
}
```

It has no idea that "Back" is in a NavigationBar, that "Settings" is the screen title, or that the cells are inside a Table. It cannot reason about screen structure, navigation state, or spatial grouping.

## Proposed Changes

### 1. Add `get_ui_tree_hierarchical()` to `ui.py`

Keep the existing `flatten_tree()` / `get_ui_tree()` for backward compatibility, but add a new function that preserves the tree structure from `idb ui describe-all`:

```python
def get_ui_tree_hierarchical(silent=False):
    """Returns the raw nested tree from idb, with each node's children intact."""
    try:
        ensure_idb_connected(silent=silent)
        output = execute_command(["idb", "ui", "describe-all"], capture_output=True)
        if not output:
            return []
        try:
            return json.loads(output)  # Return as-is, preserving nesting
        except json.JSONDecodeError:
            return []
    except subprocess.CalledProcessError as e:
        if not silent:
            msg = f"Error fetching UI tree (exit {e.returncode})"
            if e.stderr:
                msg += f": {e.stderr.strip()}"
            print(msg, file=sys.stderr)
        return []
    except Exception as e:
        if not silent:
            print(f"Error fetching UI tree: {e}", file=sys.stderr)
        return []
```

### 2. Build a simplified hierarchical output in `vision.py`

Transform the raw idb tree into a cleaner nested format:

```python
def simplify_node(node, interactive_only=False, depth=None, current_depth=0):
    """Recursively simplify a node, keeping children nested."""
    if depth is not None and current_depth > depth:
        return None

    role = node.get("role", "Unknown")
    label = node.get("AXLabel", "")
    identifier = node.get("AXIdentifier", "")
    value = node.get("AXValue", "")
    frame = node.get("frame", {})

    children = []
    for child in node.get("nodes", []):
        simplified = simplify_node(child, interactive_only, depth, current_depth + 1)
        if simplified:
            children.append(simplified)

    # In interactive_only mode, skip non-interactive nodes that have no
    # interactive descendants
    if interactive_only:
        is_interactive = role.lower().replace("ax", "") in [
            "button", "textfield", "cell", "switch", "statictext",
            "link", "image", "searchfield", "slider", "toggle",
        ]
        # Structural roles worth keeping as containers
        is_structural = role.lower().replace("ax", "") in [
            "navigationbar", "tabbar", "table", "scrollview",
            "alert", "sheet", "toolbar", "window",
        ]
        if not is_interactive and not is_structural and not children:
            return None

    result = {"type": role}
    if identifier:
        result["id"] = identifier
    if label:
        result["label"] = label
    if value:
        result["value"] = value
    if isinstance(frame, dict):
        result["frame"] = f"{frame.get('x',0)},{frame.get('y',0)},{frame.get('w',0)},{frame.get('h',0)}"
    if children:
        result["children"] = children

    return result
```

### 3. Update `inspect_cmd` to use hierarchy by default

```
pippin inspect              → hierarchical output (new default)
pippin inspect --flat       → current flat behavior (backward compat)
pippin inspect --all        → hierarchical, no filtering
pippin inspect --depth 3    → limit nesting depth
```

### Example: Hierarchical Output

```json
{
  "app": "com.apple.Preferences",
  "screen_id": "Settings",
  "elements": [
    {
      "type": "NavigationBar",
      "label": "Settings",
      "children": [
        { "type": "Button", "label": "Back" }
      ]
    },
    {
      "type": "Table",
      "children": [
        { "type": "Cell", "label": "Wi-Fi", "value": "Connected" },
        { "type": "Cell", "label": "Bluetooth", "value": "On" },
        { "type": "Cell", "label": "General" }
      ]
    },
    {
      "type": "TabBar",
      "children": [
        { "type": "Button", "label": "Settings", "value": "selected" },
        { "type": "Button", "label": "Search" }
      ]
    }
  ]
}
```

An AI reading this immediately understands: the screen is "Settings", there's a nav bar with a Back button, a table with three cells, and a tab bar with "Settings" selected.

## Testing

- Existing tests that use `inspect` with flat output should still pass when using `--flat`.
- Add tests for the hierarchical simplification logic using mock idb output.
- Verify `--depth` correctly truncates at the specified level.

## Migration

- Add a deprecation warning if `--interactive-only` is used without `--flat`, suggesting the new hierarchical default.
- The SPEC.md output schema should be updated to document the nested format.
