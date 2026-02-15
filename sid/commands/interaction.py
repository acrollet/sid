import sys
import time
from sid.utils.executor import execute_command
from sid.utils.ui import get_ui_tree, find_element, get_center

def tap_cmd(query: str = None, x: int = None, y: int = None):
    target_x, target_y = None, None

    if query:
        el = find_element(query)
        if el:
            center = get_center(el.get("frame", {}))
            if center:
                target_x, target_y = center
            else:
                print(f"Could not determine center for element '{query}'", file=sys.stderr)
        else:
             print(f"Element '{query}' not found.", file=sys.stderr)

    # Fallback to coordinates if query failed or not provided
    if target_x is None and x is not None and y is not None:
        target_x, target_y = x, y

    if target_x is not None and target_y is not None:
        try:
            execute_command(["idb", "ui", "tap", str(target_x), str(target_y)])
            print(f"Tapped at {target_x}, {target_y}")
        except Exception as e:
            print(f"Error tapping: {e}", file=sys.stderr)
    else:
        if not query and (x is None or y is None):
             print("Must provide query or coordinates.", file=sys.stderr)

def type_cmd(text: str, submit: bool = False):
    try:
        execute_command(["idb", "ui", "text", text])
        print(f"Typed: {text}")
        if submit:
             execute_command(["idb", "ui", "key-sequence", "ENTER"])
             print("Submitted.")
    except Exception as e:
        print(f"Error typing: {e}", file=sys.stderr)

def scroll_cmd(direction: str, until_visible: str = None):
    # Map direction to swipe coordinates
    w, h = 375, 812 # Default fallback

    # Try to get screen dimensions from inspect
    tree = get_ui_tree()
    if tree:
        for el in tree:
            if el.get("role") == "Window":
                f = el.get("frame", {})
                if isinstance(f, dict):
                    try:
                        w = float(f.get("w", w))
                        h = float(f.get("h", h))
                    except (ValueError, TypeError):
                        pass
                break

    cx, cy = w / 2, h / 2
    swipe_len = h * 0.4

    start_x, start_y, end_x, end_y = cx, cy, cx, cy

    if direction == "down":
        start_y = cy + swipe_len / 2
        end_y = cy - swipe_len / 2
    elif direction == "up":
        start_y = cy - swipe_len / 2
        end_y = cy + swipe_len / 2
    elif direction == "right":
        start_x = cx + w * 0.3
        end_x = cx - w * 0.3
    elif direction == "left":
        start_x = cx - w * 0.3
        end_x = cx + w * 0.3
    else:
        print(f"Invalid direction: {direction}", file=sys.stderr)
        return

    def perform_scroll():
        execute_command(["idb", "ui", "swipe", str(start_x), str(start_y), str(end_x), str(end_y)])

    if until_visible:
        max_retries = 10
        # Check first before scrolling
        if find_element(until_visible):
            print(f"Element '{until_visible}' found.")
            return

        for i in range(max_retries):
            print(f"Element '{until_visible}' not found. Scrolling {direction} ({i+1}/{max_retries})...")
            perform_scroll()
            time.sleep(1.0) # Wait for animation
            if find_element(until_visible):
                print(f"Element '{until_visible}' found.")
                return
        print(f"Element '{until_visible}' not found after scrolling.", file=sys.stderr)
    else:
        perform_scroll()
        print(f"Scrolled {direction}")

def gesture_cmd(gesture_type: str, args: list):
    if gesture_type == "swipe":
        # Expect 4 numbers. Can be in "x,y x,y" format or "x y x y"
        flat_args = []
        for arg in args:
            flat_args.extend(arg.replace(',', ' ').split())

        if len(flat_args) != 4:
             print("Usage: gesture swipe start_x,start_y end_x,end_y", file=sys.stderr)
             return

        try:
             # Validate numbers
             coords = [float(x) for x in flat_args]
             execute_command(["idb", "ui", "swipe", str(coords[0]), str(coords[1]), str(coords[2]), str(coords[3])])
             print(f"Swiped from {coords[0]},{coords[1]} to {coords[2]},{coords[3]}")
        except ValueError:
             print("Invalid coordinates for swipe.", file=sys.stderr)

    elif gesture_type == "pinch":
         print("Pinch gesture not implemented.", file=sys.stderr)
    else:
         print(f"Unknown gesture: {gesture_type}", file=sys.stderr)
