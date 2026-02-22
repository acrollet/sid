import json
import sys
from pippin.utils.executor import execute_command
from pippin.utils.ui import get_ui_tree
from pippin.utils.errors import fail, ERR_COMMAND_FAILED

def simplify_node(node, interactive_only=False, depth=None, current_depth=0, include_hidden=False):
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
        simplified = simplify_node(child, interactive_only, depth, current_depth + 1, include_hidden)
        if simplified:
            children.append(simplified)

    # Prune non-visible leaf nodes unless include_hidden is set
    if not include_hidden and node.get("visible") is False and not children:
        return None

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

    # Collapse pure wrapper nodes: if a node has no label/id/value, is not
    # a meaningful role, and has exactly one child, promote that child.
    _meaningful_roles = {
        "button", "textfield", "cell", "switch", "statictext", "link",
        "image", "searchfield", "slider", "toggle", "navigationbar",
        "tabbar", "table", "scrollview", "alert", "sheet", "toolbar",
        "window", "application",
    }
    if (not label and not identifier and not value
            and len(children) == 1
            and role.lower().replace("ax", "") not in _meaningful_roles):
        return children[0]

    result = {"type": role}
    if identifier:
        result["id"] = identifier
    if label:
        result["label"] = label
    if value:
        result["value"] = value
    if isinstance(frame, dict):
        result["frame"] = f"{frame.get('x',0)},{frame.get('y',0)},{frame.get('width', frame.get('w', 0))},{frame.get('height', frame.get('h', 0))}"
    if children:
        result["children"] = children

    return result

def inspect_cmd(interactive_only: bool = True, depth: int = None, flat: bool = False):
    if depth is not None:
        pass # Depth is now supported in simplified logic

    try:
        # Check if flat output is requested (backward compatibility)
        if flat:
            elements = get_ui_tree()
            
            # Try to detect app and screen (shared logic)
            detected_bundle = "unknown"
            detected_screen = "unknown"
            
            # We can use the flat list to detect screen info easily
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

            from pippin.utils.state import get_last_bundle_id
            detected_bundle = get_last_bundle_id() or "unknown"

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
                    frame_str = f"{frame.get('x',0)},{frame.get('y',0)},{frame.get('width', frame.get('w', 0))},{frame.get('height', frame.get('h', 0))}"
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

            result = {
                "app": detected_bundle,
                "screen_id": detected_screen,
                "elements": filtered_elements
            }
            print(json.dumps(result, indent=2))
            return

        # Hierarchical Logic
        from pippin.utils.ui import get_ui_tree_hierarchical
        tree = get_ui_tree_hierarchical()
        
        # Detect app/screen from tree root usually
        detected_bundle = "unknown"
        detected_screen = "unknown"
        
        # Helper to find screen info in tree
        def find_screen_info(nodes):
            for node in nodes:
                role = node.get("role", "")
                if role in ["Window", "AXWindow", "AXApplication"]:
                    return node.get("AXLabel") or node.get("AXIdentifier")
                # fast check children?
                # Usually window is top level or near top
            return None

        # If tree is a list (it is from idb describe-all), iterate top level
        screen_name = find_screen_info(tree)
        if screen_name:
            detected_screen = screen_name
        else:
             # Fallback: check for heading in flattened subset or just traverse a bit?
             # For simplicity, default unless we want to traverse again.
             detected_screen = "MainScreen"

        # Bundle ID from state file
        from pippin.utils.state import get_last_bundle_id
        detected_bundle = get_last_bundle_id() or "unknown"
        
        simplified_elements = []
        for node in tree:
            simplified = simplify_node(node, interactive_only, depth, include_hidden=not interactive_only)
            if simplified:
                simplified_elements.append(simplified)
        
        result = {
            "app": detected_bundle,
            "screen_id": detected_screen,
            "elements": simplified_elements
        }
        

        print(json.dumps(result, indent=2))

    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Could not inspect UI: {e}")

from pippin.utils.device import get_simctl_target

def screenshot_cmd(filename: str, mask_text: bool = False):
    if mask_text:
        print("WARNING: Text masking is not implemented.", file=sys.stderr)

    try:
        udid = get_simctl_target()
        execute_command(["xcrun", "simctl", "io", udid, "screenshot", filename])
        print(json.dumps({"status": "success", "action": "screenshot", "file": filename}))
    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Screenshot failed: {e}")
