# Replace idb with WebDriverAgent in Pippin

## Context

Pippin uses Facebook's `idb` for UI inspection and interaction, but `idb ui describe-all` can't see into WKWebView content — it returns an empty tree when a web view is the primary content. WebDriverAgent (WDA) uses XCUITest under the hood, which has deep accessibility traversal including web views. Additionally, `fb-idb` is archived/unmaintained by Meta, making this a good time to switch.

The goal: replace all idb usage with WDA + simctl, drop the `fb-idb` dependency, and gain web view visibility.

## How WDA Works

- Pre-built `.app` bundles available from [appium/WebDriverAgent releases](https://github.com/appium/WebDriverAgent/releases)
  - Simulator (Apple Silicon): `WebDriverAgentRunner-Build-Sim-arm64.zip`
  - Simulator (Intel): `WebDriverAgentRunner-Build-Sim-x86_64.zip`
- Install via `xcrun simctl install <udid> <path-to-.app>`
- Launch via `xcrun simctl launch --terminate-running-process <udid> com.facebook.WebDriverAgentRunner.xctrunner`
- Port config via env var: `SIMCTL_CHILD_USE_PORT=8100`
- Exposes REST API on `localhost:8100`
- Requires a session (`POST /session`) before queries
- `/source` returns XML accessibility tree; element queries use XCUITest internally

## Current idb Usage (all 7 patterns to replace)

| # | idb Command | File | Replacement |
|---|-------------|------|-------------|
| 1 | `idb connect <udid>` | `utils/ui.py` | Remove (not needed) |
| 2 | `idb ui describe-all --udid <udid>` | `utils/ui.py` | `wda.get_source_tree()` |
| 3 | `idb ui tap --udid <udid> <x> <y>` | `commands/interaction.py` | `wda.tap(x, y)` |
| 4 | `idb ui text --udid <udid> <text>` | `commands/interaction.py` | `wda.type_text(text)` |
| 5 | `idb ui key-sequence --udid <udid> ENTER` | `commands/interaction.py` | `wda.press_key("ENTER")` |
| 6 | `idb ui swipe --udid ... <x1> <y1> <x2> <y2>` | `commands/interaction.py` | `wda.swipe(x1, y1, x2, y2, duration)` |
| 7 | `idb set-location --udid <udid> <lat> <lon>` | `commands/system.py` | `xcrun simctl location <udid> set <lat>,<lon>` |

## Files to Modify

| File | Change |
|------|--------|
| `pippin/utils/wda.py` | **NEW** — WDA HTTP client, session mgmt, XML-to-JSON translation |
| `pippin/utils/ui.py` | Replace idb calls with `wda.get_source_tree()` |
| `pippin/commands/interaction.py` | Replace idb tap/type/swipe with wda client calls |
| `pippin/commands/system.py` | Replace `idb set-location` with `xcrun simctl location` |
| `pippin/commands/doctor.py` | Replace idb checks/install with WDA checks/download |
| `pippin/main.py` | No changes needed |
| `pyproject.toml` | Remove `fb-idb` dependency |
| `tests/test_commands.py` | Update mocks from idb assertions to wda function mocks |
| `tests/test_wda.py` | **NEW** — Unit tests for XML-to-JSON translation |

## Implementation Steps

### 1. Create `pippin/utils/wda.py`

Core module using stdlib only (`urllib.request`, `xml.etree.ElementTree`, `json`):

**HTTP & Session:**
- `_wda_request(method, path, body=None)` — Low-level HTTP helper, returns parsed JSON
- `get_session()` — Lazy-init session via `POST /session`, cached in module global. Retries once on stale session (404).
- `ensure_wda_running()` — `GET /status`, return True/False

**UI Tree:**
- `get_source_tree()` — `GET /session/{id}/source`, parse XML, convert to idb-compatible dict format
- `_xml_to_element(xml_node)` — Recursive converter:
  - `type` (strip `XCUIElementType` prefix) → `role`
  - `name` → `AXIdentifier`
  - `label` → `AXLabel`
  - `value` → `AXValue`
  - `x,y,width,height` → `frame: {x, y, width, height}` (as floats)
  - child XML elements → `nodes: [...]`

**Interaction:**
- `tap(x, y)` — `POST /session/{id}/wda/tap/0` with `{"x": x, "y": y}`
- `type_text(text)` — `POST /session/{id}/wda/keys` with `{"value": list(text)}`
- `press_key(key)` — For ENTER, send `"\n"` via same keys endpoint
- `swipe(x1, y1, x2, y2, duration)` — `POST /session/{id}/wda/dragfromtoforduration`

**Lifecycle:**
- `install_wda()` — Download pre-built bundle from GitHub releases API to `~/.pippin/wda/`, install via `xcrun simctl install`
- `start_wda(udid)` — `xcrun simctl launch --terminate-running-process <udid> com.facebook.WebDriverAgentRunner.xctrunner`, poll `/status` for up to 15s
- `_get_wda_bundle_path()` — Check `~/.pippin/wda/` for existing bundle

### 2. Update `pippin/utils/ui.py`

- Remove `ensure_idb_connected()`
- `get_ui_tree()` → call `wda.get_source_tree()`, then `flatten_tree()`
- `get_ui_tree_hierarchical()` → call `wda.get_source_tree()` directly
- `find_element()`, `get_center()`, `flatten_tree()` — unchanged (they operate on the normalized dict format)

### 3. Update `pippin/commands/interaction.py`

- `tap_cmd()`: replace `execute_command(["idb", "ui", "tap", ...])` with `wda.tap(ix, iy)`
- `type_cmd()`: replace `idb ui text` with `wda.type_text(text)`, `idb ui key-sequence ENTER` with `wda.press_key("ENTER")`
- `scroll_cmd()` / `gesture_cmd()`: replace `idb ui swipe` with `wda.swipe(...)`
- Remove `execute_command` and `get_target_udid` imports (no longer needed)

### 4. Update `pippin/commands/system.py`

Replace `idb set-location` with:
```python
execute_command(["xcrun", "simctl", "location", udid, "set", f"{lat},{lon}"])
```

### 5. Update `pippin/commands/doctor.py`

- Remove `_install_idb()` function
- Remove `idb` from dependency checks
- Add WDA checks: look for bundle at `~/.pippin/wda/`, offer to download if missing, check if WDA is responding

### 6. Update `pyproject.toml`

Remove `fb-idb` from dependencies. No new deps needed (stdlib only for HTTP/XML).

### 7. Update tests

- `test_commands.py`: change mocks from `execute_command(["idb", ...])` assertions to `@patch('pippin.utils.wda.tap')` etc.
- New `test_wda.py`: test `_xml_to_element()` with sample XML snippets, test session retry logic

## Verification

1. `pippin doctor` — should check for WDA, offer download, verify it starts
2. `pippin inspect` on a native screen — should return element tree
3. `pippin inspect` on a screen with WKWebView — should show web content elements (StaticText, Link, etc. inside the WebView)
4. `pippin tap "some label"` — should find and tap elements
5. `pippin context` on the Lirum reader view — should show article content that was previously invisible
6. `python -m pytest tests/` — all tests pass

## Risks

- **WDA `/source` depth for web views**: The `/source` endpoint uses XCUITest snapshots which should include web view content, but depth may be limited. If web content doesn't appear, element-finding queries (`POST /elements`) go deeper.
- **Session staleness**: Handled by retry-on-404 in `get_session()`.
- **Pre-built bundle URL changes**: Use GitHub releases API dynamically rather than hardcoding versions.
- **simctl location syntax**: Verify exact syntax on target Xcode version during implementation.
