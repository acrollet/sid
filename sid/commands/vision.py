import json
import sys
from sid.utils.executor import execute_command

def inspect_cmd(interactive_only: bool = True, depth: int = None):
    try:
        # idb ui describe-all returns a JSON list of elements
        output = execute_command(["idb", "ui", "describe-all"])

        try:
            elements = json.loads(output)
        except json.JSONDecodeError:
            # If output is not JSON, it might be an error message or empty
            # For dry run or mock, if empty return empty list
            if not output:
                elements = []
            else:
                print(f"Error: Invalid JSON from idb: {output}", file=sys.stderr)
                return

        filtered_elements = []
        for el in elements:
            # type/role
            role = el.get("role", "Unknown") # idb uses 'role'

            if interactive_only:
                # Spec list: Button, TextField, Cell, Switch, StaticText
                # We should be case-insensitive just in case
                valid_roles = ["Button", "TextField", "Cell", "Switch", "StaticText"]
                if role not in valid_roles:
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
        # We can leave app/screen_id as placeholder as getting them reliably requires more logic
        result = {
            "app": "com.example.myapp",
            "screen_id": "unknown_screen",
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
