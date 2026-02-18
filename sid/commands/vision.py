import json
import sys
from sid.utils.executor import execute_command
from sid.utils.ui import get_ui_tree, get_ui_tree_hierarchical

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
            "alert", "sheet", "toolbar", "window", "application",
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

def inspect_cmd(interactive_only: bool = True, depth: int = None, flat: bool = False):
    if depth is not None and flat:
        print("WARNING: Depth filtering is not fully supported in flat mode.", file=sys.stderr)

    try:
        # Detect app (common)
        detected_bundle = "unknown"
        from sid.commands.verification import STATE_FILE
        import os
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    detected_bundle = f.read().strip()
            except IOError:
                pass

        detected_screen = "unknown"

        if flat:
            elements = get_ui_tree()

            # Try to detect screen
            for el in elements:
                role = el.get("role", "")
                if role in ["Window", "AXWindow", "AXApplication"]:
                    detected_screen = el.get("AXLabel") or el.get("AXIdentifier") or "MainScreen"
                    break

            if detected_screen == "unknown":
                 for el in elements:
                      if el.get("role") in ["Heading", "AXHeading"]:
                           detected_screen = el.get("AXLabel") or "MainScreen"
                           break

            filtered_elements = []
            for el in elements:
                role = el.get("role", "Unknown")

                if interactive_only:
                    valid_roles = [
                        "button", "textfield", "cell", "switch", "statictext", "link", "image", "searchfield",
                        "axbutton", "axtextfield", "axcell", "axswitch", "axstatictext", "axlink", "aximage", "axsearchfield"
                    ]
                    if role.lower() not in valid_roles:
                         continue

                frame = el.get("frame", {})
                if isinstance(frame, dict):
                    frame_str = f"{frame.get('x',0)},{frame.get('y',0)},{frame.get('w',0)},{frame.get('h',0)}"
                else:
                    frame_str = str(frame)

                mapped = {
                    "id": el.get("AXIdentifier", ""),
                    "label": el.get("AXLabel", ""),
                    "type": role,
                    "frame": frame_str,
                    "value": el.get("AXValue", "")
                }

                filtered_elements.append(mapped)

            final_elements = filtered_elements

        else:
            # Hierarchical Mode
            raw_tree = get_ui_tree_hierarchical()

            root_nodes = []
            if isinstance(raw_tree, list):
                root_nodes = raw_tree
            elif isinstance(raw_tree, dict):
                root_nodes = [raw_tree]

            # Detect screen
            for node in root_nodes:
                role = node.get("role", "")
                if role in ["Window", "AXWindow", "AXApplication"]:
                     detected_screen = node.get("AXLabel") or node.get("AXIdentifier") or "MainScreen"
                     break

            final_elements = []
            for node in root_nodes:
                simplified = simplify_node(node, interactive_only, depth)
                if simplified:
                    final_elements.append(simplified)

        result = {
            "app": detected_bundle,
            "screen_id": detected_screen if detected_screen != "unknown" else "MainScreen",
            "elements": final_elements
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error inspecting UI: {e}", file=sys.stderr)

def screenshot_cmd(filename: str, mask_text: bool = False):
    if mask_text:
        print("WARNING: Text masking is not implemented.", file=sys.stderr)

    try:
        execute_command(["xcrun", "simctl", "io", "booted", "screenshot", filename])
        print(f"Screenshot saved to {filename}")
    except Exception as e:
        print(f"Error taking screenshot: {e}", file=sys.stderr)
