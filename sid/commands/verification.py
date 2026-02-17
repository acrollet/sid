import sys
import os
import time
from sid.utils.executor import execute_command
from sid.utils.ui import find_element

STATE_FILE = "/tmp/sid_last_bundle_id"

def wait_cmd(query: str, timeout: float = 10.0, state: str = "visible"):
    """Waits for an element to reach a certain state."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        el = find_element(query)
        if state == "visible" or state == "exists":
            if el:
                print(f"PASS: Element '{query}' is {state}.")
                return
        elif state == "hidden":
            if not el:
                print(f"PASS: Element '{query}' is hidden.")
                return
        time.sleep(0.5)
    
    print(f"FAIL: ERR_TIMEOUT: Timeout waiting {timeout}s for '{query}' to be {state}.")
    sys.exit(1)

def assert_cmd(query: str, state: str):
    el = find_element(query)

    if state == "exists" or state == "visible":
        if el:
            print("PASS")
        else:
            print(f"FAIL: ERR_ELEMENT_NOT_FOUND: Element '{query}' not found.")
            sys.exit(1)

    elif state == "hidden":
        if not el:
            print("PASS")
        else:
            print(f"FAIL: ERR_ELEMENT_EXISTS: Element '{query}' found (expected hidden).")
            sys.exit(1)

    elif state.startswith("text="):
        expected_text = state.split("=", 1)[1]
        if not el:
             print(f"FAIL: ERR_ELEMENT_NOT_FOUND: Element '{query}' not found.")
             sys.exit(1)

        actual_text = el.get("AXValue") or el.get("AXLabel") or ""
        if str(actual_text) == expected_text:
             print("PASS")
        else:
             print(f"FAIL: ERR_TEXT_MISMATCH: Element found but text was '{actual_text}', expected '{expected_text}'")
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
        print("ERR_NO_TARGET_APP: Could not determine target app. Run 'sid launch' first.", file=sys.stderr)
        return

    if crash_report:
        # Crash logs on macOS for simulators are typically in ~/Library/Logs/DiagnosticReports
        # and named like "AppName-YYYY-MM-DD-HHMMSS.ips"
        # Since we are in a simulator, they might also be inside the simulator's own diagnostic path.
        search_paths = [
            os.path.expanduser("~/Library/Logs/DiagnosticReports"),
        ]
        
        # Try to find the most recent .ips file containing the bundle_id or app name
        # For simplicity, we'll look for files matching the bundle_id (often part of the process name)
        # and sort by modification time.
        found_report = None
        latest_time = 0
        
        # bundle_id usually looks like 'com.company.AppName', we want 'AppName'
        app_name = bundle_id.split(".")[-1]

        for path in search_paths:
            if not os.path.exists(path):
                continue
            for f in os.listdir(path):
                if f.endswith(".ips") and app_name in f:
                    full_path = os.path.join(path, f)
                    mtime = os.path.getmtime(full_path)
                    if mtime > latest_time:
                        latest_time = mtime
                        found_report = full_path

        if found_report:
            print(f"CRASH_REPORT_FOUND: {found_report}")
            try:
                with open(found_report, "r") as rf:
                    # IPS files are JSON-like but often contain a header. 
                    # We'll just output the first 100 lines for the LLM.
                    content = rf.readlines()
                    print("--- STACK TRACE ---")
                    print("".join(content[:100]))
            except Exception as e:
                print(f"ERR_READING_CRASH_LOG: {e}", file=sys.stderr)
        else:
            print("NO_CRASH_REPORT_FOUND")
        return

    # Use 'subsystem' as a proxy for bundle_id filtering, or just dump recent logs
    cmd = ["xcrun", "simctl", "spawn", "booted", "log", "show", "--style", "compact", "--predicate", f"subsystem == \"{bundle_id}\"", "--last", "5m"]

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
        print("ERR_NO_TARGET_APP: Could not determine target app. Run 'sid launch' first.", file=sys.stderr)
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
