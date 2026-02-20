import json
import sys
import os
from pippin.utils.executor import execute_command
from pippin.utils.ui import get_ui_tree_hierarchical
from pippin.commands.vision import simplify_node, screenshot_cmd
from pippin.utils.state import get_last_bundle_id
from pippin.utils.errors import fail, ERR_COMMAND_FAILED, EXIT_COMMAND_FAILED

from pippin.utils.device import get_target_udid

def get_device_info():
    """Get info about the booted simulator."""
    try:
        output = execute_command(
            ["xcrun", "simctl", "list", "devices", "booted", "--json"],
            capture_output=True
        )
        if not output:
             return None
        
        data = json.loads(output)
        devices = data.get("devices", {})
        
        target_udid = None
        try:
            target_udid = get_target_udid()
        except:
            pass # If ambiguous or failed, we might default or show all? 
                 # But context usually needs specific device context.
        
        for runtime, dev_list in devices.items():
            for dev in dev_list:
                if dev.get("state") == "Booted":
                    # If target set, filter. Else return first booted (legacy/auto behavior matches get_target_udid logic)
                    if target_udid and dev.get("udid") != target_udid:
                        continue
                        
                    return {
                        "udid": dev.get("udid"),
                        "name": dev.get("name"),
                        "runtime": runtime.split(".")[-1], # Approximate runtime name
                        "state": "Booted"
                    }
        return None
    except Exception:
        return None

def get_app_info():
    """Get info about the running app."""
    bundle_id = get_last_bundle_id()
    
    return {
        "bundle_id": bundle_id,
        "state": "running" if bundle_id else "unknown" # simplified state
    }

def analyze_screen(tree):
    """Extract high-level screen context from the UI tree."""
    info = {
        "title": None,
        "breadcrumb": [],
        "focused_element": None,
        "alert": None,
    }

    def walk(node, depth=0):
        role = node.get("role", "")
        label = node.get("AXLabel", "")
        identifier = node.get("AXIdentifier", "")
        
        # Breadcrumbs & Title from NavigationBar
        if role == "NavigationBar":
             # usually identifier is the title
             if identifier:
                 info["title"] = identifier
             elif label:
                 info["title"] = label
             
             # Look for children that might be back buttons
             if "nodes" in node:
                 for child in node["nodes"]:
                     child_role = child.get("role", "")
                     child_label = child.get("AXLabel", "")
                     if child_role == "Button" and child_label:
                         # Heuristic: Back buttons often are at the left or have specific labels
                         # For now, just collecting buttons in navbar might be too noisy, 
                         # but let's assume non-title buttons are nav mechanics
                         if child_label not in [info["title"], "Edit", "Done", "Add"]:
                              info["breadcrumb"].append(child_label)

        # Alert detection
        if role in ["Alert", "Sheet"]:
            info["alert"] = {
                "title": label,
                "message": next((c.get("AXLabel") for c in node.get("nodes", []) if c.get("role") == "StaticText"), "")
            }

        # Focused element (keyboard connected)
        # idb doesn't strictly give "focused" state easily in all versions, 
        # but we can look for "has_keyboard_focus" if available or infer.
        # For now, let's skip complex focus inference unless explicitly marked.
        
        if "nodes" in node:
            for child in node["nodes"]:
                walk(child, depth + 1)

    if isinstance(tree, list):
        for node in tree:
            walk(node)
    
    return info

def get_recent_logs(lines=20):
    """Fetch the last N lines of system logs."""
    # This is expensive and tricky to filter correctly without a predicate.
    # For now, we'll try to get logs for the simulator, but filtering by app is hard 
    # without a known pid.
    # We will return null for now as per design to verify mechanics 
    # or implement a simple log dump.
    return None

def context_cmd(include_logs: bool = False, screenshot_path: str = None, brief: bool = False):
    result = {}

    try:
        # 1. Device info
        result["device"] = get_device_info()

        # 2. App info
        result["app"] = get_app_info()

        # 3. Screen analysis
        tree = get_ui_tree_hierarchical()
        result["screen"] = analyze_screen(tree)

        # 4. UI hierarchy
        if not brief:
            result["ui"] = [simplify_node(n) for n in tree]
        
        # 5. Optional logs
        if include_logs:
            result["logs"] = get_recent_logs()

        # 6. Optional screenshot
        if screenshot_path:
            screenshot_cmd(screenshot_path)
            result["screenshot"] = screenshot_path

        print(json.dumps(result, indent=2))
        
    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Context command failed: {e}", EXIT_COMMAND_FAILED)
