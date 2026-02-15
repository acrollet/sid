import sys
import json
from sid.utils.executor import execute_command

def get_ui_tree():
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

def find_element(query: str):
    elements = get_ui_tree()
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
