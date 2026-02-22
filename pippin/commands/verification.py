import sys
import os
import time
import json
from pippin.utils.executor import execute_command
from pippin.utils.ui import find_element
from pippin.utils.errors import (
    fail, EXIT_SUCCESS, EXIT_TIMEOUT, EXIT_ELEMENT_NOT_FOUND, EXIT_COMMAND_FAILED,
    ERR_TIMEOUT, ERR_ELEMENT_NOT_FOUND, ERR_TEXT_MISMATCH, ERR_NO_TARGET_APP, ERR_COMMAND_FAILED
)

from pippin.utils.state import get_last_bundle_id

def wait_cmd(query: str, timeout: float = 10.0, state: str = "visible", strict: bool = False, scroll: bool = False):
    """Waits for an element to reach a certain state."""
    start_time = time.time()
    from pippin.utils.ui import is_onscreen
    from pippin.commands.interaction import scroll_cmd

    while time.time() - start_time < timeout:
        el = find_element(query, silent=True, strict=strict)
        if state == "visible":
            if el and is_onscreen(el):
                print(json.dumps({"status": "success", "action": "wait", "query": query, "state": state}))
                return
            elif scroll and not (el and is_onscreen(el)):
                scroll_cmd("down", silent=True)
        elif state == "exists":
            if el:
                print(json.dumps({"status": "success", "action": "wait", "query": query, "state": state}))
                return
        elif state == "hidden":
            if not el or not is_onscreen(el):
                print(json.dumps({"status": "success", "action": "wait", "query": query, "state": state}))
                return
        time.sleep(0.5)
    
    fail(ERR_TIMEOUT, f"Timeout waiting {timeout}s for '{query}' to be {state}.", EXIT_TIMEOUT)

def assert_cmd(query: str, state: str, strict: bool = False):
    from pippin.utils.ui import is_onscreen
    el = find_element(query, strict=strict)

    if state == "exists":
        if el:
            print(json.dumps({"status": "success", "action": "assert", "query": query, "state": state}))
        else:
            fail(ERR_ELEMENT_NOT_FOUND, f"Element '{query}' not found.", EXIT_ELEMENT_NOT_FOUND)

    elif state == "visible":
        if el and is_onscreen(el):
            print(json.dumps({"status": "success", "action": "assert", "query": query, "state": state}))
        else:
            fail(ERR_ELEMENT_NOT_FOUND, f"Element '{query}' not found or not visible on screen.", EXIT_ELEMENT_NOT_FOUND)

    elif state == "hidden":
        if not el or not is_onscreen(el):
            print(json.dumps({"status": "success", "action": "assert", "query": query, "state": state}))
        else:
            # Using EXIT_ELEMENT_NOT_FOUND semantics loosely here, or just generic failure
            fail("ERR_ELEMENT_EXISTS", f"Element '{query}' found and visible (expected hidden).", EXIT_COMMAND_FAILED)

    elif state.startswith("text="):
        expected_text = state.split("=", 1)[1]
        if not el:
             fail(ERR_ELEMENT_NOT_FOUND, f"Element '{query}' not found.", EXIT_ELEMENT_NOT_FOUND)

        actual_text = el.get("AXValue") or el.get("AXLabel") or ""
        if str(actual_text) == expected_text:
             print(json.dumps({"status": "success", "action": "assert", "query": query, "state": state}))
        else:
             fail(ERR_TEXT_MISMATCH, f"Element found but text was '{actual_text}', expected '{expected_text}'", EXIT_COMMAND_FAILED)
    else:
        fail("ERR_INVALID_ARGS", f"Unknown state: {state}", EXIT_COMMAND_FAILED)

def logs_cmd(crash_report: bool = False):
    bundle_id = None
    bundle_id = get_last_bundle_id()

    if not bundle_id:
        fail(ERR_NO_TARGET_APP, "Could not determine target app. Run 'pippin launch' first.", EXIT_COMMAND_FAILED)

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
            try:
                with open(found_report, "r") as rf:
                    # IPS files are JSON-like but often contain a header. 
                    # We'll just output the first 100 lines for the LLM.
                    content = rf.readlines()
                    # Output JSON wrapper? Or just raw text since logs are unstructured?
                    # Let's keep it raw for logs/crash reports as they are large.
                    print(f"CRASH_REPORT_FOUND: {found_report}")
                    print("--- STACK TRACE ---")
                    print("".join(content[:100]))
            except Exception as e:
                fail(ERR_COMMAND_FAILED, f"Error reading crash log: {e}")
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
        fail(ERR_COMMAND_FAILED, f"Error fetching logs: {e}")

def tree_cmd(directory: str):
    bundle_id = None
    bundle_id = get_last_bundle_id()

    if not bundle_id:
        fail(ERR_NO_TARGET_APP, "Could not determine target app. Run 'pippin launch' first.", EXIT_COMMAND_FAILED)

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
             fail(ERR_COMMAND_FAILED, "Could not find app container.")

        target_path = os.path.join(container, subpath)

        if not os.path.exists(target_path):
             fail(ERR_COMMAND_FAILED, f"Directory {target_path} does not exist.")

        # List files using ls -R to be tree-like
        output = execute_command(["ls", "-R", target_path])
        print(output)

    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Error listing files: {e}")
