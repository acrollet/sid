import json
import sys
from sid.utils.executor import execute_command
from sid.utils.ui import get_ui_tree

def inspect_cmd(interactive_only: bool = True, depth: int = None):
    if depth is not None:
        print("WARNING: Depth filtering is not fully supported yet.", file=sys.stderr)

    try:
        elements = get_ui_tree()

        # Try to detect app and screen
        detected_bundle = "unknown"
        detected_screen = "unknown"

        # In idb's output, the top-level window often has the bundle_id in its metadata 
        # or we can look for the 'Window' role.
        for el in elements:
            role = el.get("role", "")
            if role in ["Window", "AXWindow", "AXApplication"]:
                # Some idb versions provide bundle_id in the window node or we can infer it
                # For now, we'll see if AXIdentifier or AXLabel on Window gives us a screen name
                detected_screen = el.get("AXLabel") or el.get("AXIdentifier") or "MainScreen"
                break
        
        if detected_screen == "unknown":
             # Try to find a heading as a fallback
             for el in elements:
                  if el.get("role") in ["Heading", "AXHeading"]:
                       detected_screen = el.get("AXLabel") or "MainScreen"
                       break

        # If we have a state file, use that as a fallback/source for bundle_id
        from sid.commands.verification import STATE_FILE
        import os
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    detected_bundle = f.read().strip()
            except IOError:
                pass

        filtered_elements = []
        for el in elements:
            # type/role
            role = el.get("role", "Unknown") # idb uses 'role'

            if interactive_only:
                # Spec list: Button, TextField, Cell, Switch, StaticText
                # We should be case-insensitive and handle AX prefixes
                valid_roles = [
                    "button", "textfield", "cell", "switch", "statictext", "link", "image", "searchfield",
                    "axbutton", "axtextfield", "axcell", "axswitch", "axstatictext", "axlink", "aximage", "axsearchfield"
                ]
                if role.lower() not in valid_roles:
                     continue

            # Helper to format frame
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

        # Attempt to get running app
        result = {
            "app": detected_bundle,
            "screen_id": detected_screen,
            "elements": filtered_elements
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
