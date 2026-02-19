import sys
import json
import subprocess
from pippin.utils.executor import execute_command
from pippin.utils.device import get_target_udid

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
    """Ensures idb is connected to the simulator."""
    # idb needs explicit connection sometimes, especially for new sims.
    # We'll try to connect to the target.
    # If no target specified, idb connect <booted> logic is implied or we resolve it.
    
    try:
        udid = get_target_udid()
        # "idb connect <udid>"
        execute_command(["idb", "connect", udid], check=False, capture_output=True)
        return True
    except Exception:
        return False # Best effort

def get_ui_tree(silent=False):
    """Returns a flat list of UI elements from idb."""
    try:
        ensure_idb_connected(silent=silent)
        udid = get_target_udid()
        output = execute_command(["idb", "ui", "describe-all", "--udid", udid], capture_output=True)
        if not output:
            return []
        try:
            data = json.loads(output)
            # define flatten helper inside or used from specialized function
            flat = flatten_tree(data)
            return flat
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

def get_ui_tree_hierarchical(silent=False):
    """Returns the raw nested tree from idb, with each node's children intact."""
    try:
        ensure_idb_connected(silent=silent)
        udid = get_target_udid()
        output = execute_command(["idb", "ui", "describe-all", "--udid", udid], capture_output=True)
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

def find_element(query: str, silent=False, strict=False):
    elements = get_ui_tree(silent=silent)
    if not elements:
        return None

    query_lower = query.lower()
    
    # Check for type:label syntax
    element_type = None
    if ":" in query and not query.startswith("http"):
        parts = query.split(":", 1)
        if len(parts) == 2:
            element_type, query_val = parts
            element_type = element_type.lower()
            query_lower = query_val.lower()
            # We use query_val for matching now
    else:
        query_val = query

    exact_id = []
    exact_label = []
    substring_label = []

    for el in elements:
        # Filter by type if specified
        if element_type:
            role = (el.get("role") or "").lower().replace("ax", "")
            if role != element_type:
                continue

        # Tier 1: Exact accessibility identifier
        if el.get("AXIdentifier") == query_val:
            exact_id.append(el)

        label = (el.get("AXLabel") or "")
        label_lower = label.lower()

        # Tier 2: Exact label match (case-insensitive)
        if label_lower == query_lower:
            exact_label.append(el)

        # Tier 3: Substring match (skip in strict mode)
        elif not strict and query_lower in label_lower:
            substring_label.append(el)

    # Return best match
    if exact_id:
        if len(exact_id) > 1 and not silent:
            # Identifier should ideally be unique, but if not, warn.
            print(f"WARN: {len(exact_id)} elements matched id '{query_val}', using first.", file=sys.stderr)
        return exact_id[0]

    if exact_label:
        if len(exact_label) > 1 and not silent:
            print(f"WARN: {len(exact_label)} elements matched label '{query_val}', using first.", file=sys.stderr)
            match_labels = [e.get('AXLabel') for e in exact_label[:5]]
            print(f"      Matches: {match_labels}", file=sys.stderr)
        return exact_label[0]

    if substring_label:
        if len(substring_label) > 1 and not silent:
            print(f"WARN: {len(substring_label)} elements contain '{query_val}' in label, using first.", file=sys.stderr)
            match_labels = [e.get('AXLabel') for e in substring_label[:5]]
            print(f"      Matches: {match_labels} ...", file=sys.stderr)
        return substring_label[0]

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
