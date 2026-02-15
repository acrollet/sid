import sys
import os
import json
from sid.utils.executor import execute_command

STATE_FILE = "/tmp/sid_last_bundle_id"

def _get_ui_tree():
    try:
        output = execute_command(["idb", "ui", "describe-all"], capture_output=True)
        if not output:
            return []
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return []
    except Exception as e:
        print(f"Error fetching UI tree: {e}", file=sys.stderr)
        return []

def _find_element(query: str):
    elements = _get_ui_tree()
    if not elements:
        return None
    # 1. Exact Match: Accessibility Identifier
    for el in elements:
        if el.get("AXIdentifier") == query:
            return el

    # 2. Fuzzy Match: Label text
    query_lower = query.lower()
    for el in elements:
        label = el.get("AXLabel", "")
        if label and query_lower in label.lower():
            return el

    return None

def assert_cmd(query: str, state: str):
    el = _find_element(query)

    if state == "exists" or state == "visible":
        if el:
            print("PASS")
        else:
            print(f"FAIL: Element '{query}' not found.")
            sys.exit(1)

    elif state == "hidden":
        if not el:
            print("PASS")
        else:
            print(f"FAIL: Element '{query}' found (expected hidden).")
            sys.exit(1)

    elif state.startswith("text="):
        expected_text = state.split("=", 1)[1]
        if not el:
             print(f"FAIL: Element '{query}' not found.")
             sys.exit(1)

        actual_text = el.get("AXValue") or el.get("AXLabel") or ""
        if str(actual_text) == expected_text:
             print("PASS")
        else:
             print(f"FAIL: Element found but text was '{actual_text}', expected '{expected_text}'")
             sys.exit(1)
    else:
        print(f"Unknown state: {state}", file=sys.stderr)
        sys.exit(1)

def logs_cmd(crash_report: bool = False):
    bundle_id = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                bundle_id = f.read().strip()
        except IOError:
            pass

    if not bundle_id:
        print("Error: Could not determine target app. Run 'sid launch' first.", file=sys.stderr)
        return

    # Use 'subsystem' as a proxy for bundle_id filtering, or just dump recent logs
    cmd = ["xcrun", "simctl", "spawn", "booted", "log", "show", "--style", "compact", "--predicate", f"subsystem == \"{bundle_id}\"", "--last", "5m"]

    if crash_report:
        # Just show logs, maybe grep for crash?
        print("Checking logs for crash reports...", file=sys.stderr)
        # We could add "and eventMessage contains 'crash'" to predicate

    try:
        # Print logs to stdout
        output = execute_command(cmd, capture_output=True)
        print(output)
    except Exception as e:
        print(f"Error fetching logs: {e}", file=sys.stderr)

def tree_cmd(directory: str):
    bundle_id = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                bundle_id = f.read().strip()
        except IOError:
            pass

    if not bundle_id:
        print("Error: Could not determine target app. Run 'sid launch' first.", file=sys.stderr)
        return

    subpath = ""
    if directory == "documents":
        subpath = "Documents"
    elif directory == "caches":
        subpath = "Library/Caches"
    elif directory == "tmp":
        subpath = "tmp"
    else:
        subpath = directory

    try:
        container = execute_command(["xcrun", "simctl", "get_app_container", "booted", bundle_id, "data"])
        if not container:
             print("Could not find app container.", file=sys.stderr)
             return

        target_path = os.path.join(container, subpath)

        if not os.path.exists(target_path):
             print(f"Directory {target_path} does not exist.", file=sys.stderr)
             return

        # List files using ls -R to be tree-like
        output = execute_command(["ls", "-R", target_path])
        print(output)

    except Exception as e:
        print(f"Error listing files: {e}", file=sys.stderr)
