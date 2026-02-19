import sys
import json
import subprocess
from pippin.utils.executor import execute_command

def flatten_tree(nodes):
    flat_list = []
    if not isinstance(nodes, list):
        return flat_list
    for node in nodes:
        flat_list.append(node)
        if "nodes" in node:
            flat_list.extend(flatten_tree(node["nodes"]))
    return flat_list

def ensure_idb_connected(silent=False):
    """Ensures idb is connected to the booted simulator."""
    try:
        targets = execute_command(["idb", "list-targets"], capture_output=True)
        if not targets:
            return False
            
        booted_udid = None
        needs_connect = False
        
        for line in targets.split("\n"):
            if "booted" in line.lower():
                parts = line.split("|")
                if len(parts) >= 2:
                    booted_udid = parts[1].strip()
                    if "no companion connected" in line.lower():
                        needs_connect = True
                    break
        
        if needs_connect and booted_udid:
            if not silent:
                print(f"Connecting idb companion to booted simulator ({booted_udid})...", file=sys.stderr)
            execute_command(["idb", "connect", booted_udid], capture_output=True)
            return True
        return booted_udid is not None
    except Exception as e:
        if not silent:
            print(f"Warning: Failed to ensure idb connection: {e}", file=sys.stderr)
        return False

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

def get_ui_tree(silent=False):
    try:
        ensure_idb_connected(silent=silent)
        output = execute_command(["idb", "ui", "describe-all"], capture_output=True)
        if not output:
            return []
        try:
            tree = json.loads(output)
            return flatten_tree(tree)
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

def find_element(query: str, silent=False):
    elements = get_ui_tree(silent=silent)
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
        # Check if label contains query or matches
        if label and query_lower in label.lower():
            return el

    return None

def get_center(frame):
    if isinstance(frame, dict):
        try:
            x = float(frame.get('x', 0))
            y = float(frame.get('y', 0))
            w = float(frame.get('w', 0))
            h = float(frame.get('h', 0))
            return x + w / 2, y + h / 2
        except (ValueError, TypeError):
            return None
    return None
