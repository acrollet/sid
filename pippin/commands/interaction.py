import sys
import time
import json
from pippin.utils.ui import get_ui_tree, find_element, get_center
from pippin.utils import wda
from pippin.utils.errors import (
    fail, EXIT_ELEMENT_NOT_FOUND, EXIT_COMMAND_FAILED, EXIT_INVALID_ARGS,
    ERR_ELEMENT_NOT_FOUND, ERR_COORDINATES_NOT_FOUND, ERR_COMMAND_FAILED, ERR_INVALID_ARGS
)

def tap_cmd(query: str = None, x: int = None, y: int = None, strict: bool = False, scroll: bool = False):
    target_x, target_y = x, y
    
    if query:
        # Try to find element by ID or Label
        element = find_element(query, strict=strict)
        
        if not element and scroll:
            print(f"Element '{query}' not found, auto-scrolling to find it...", file=sys.stderr)
            scroll_cmd("down", until_visible=query, silent=True)
            element = find_element(query, strict=strict)

        if element:
            frame = element.get("frame")
            center = get_center(frame)
            if center:
                target_x, target_y = center
                
                # Heuristic for zero-width elements (like in Lirum)
                # If width is 0, we can't reliably tap it at x=0. 
                # We should tap the middle of the screen at that Y.
                try:
                    w = float(frame.get("width", frame.get("w", 0)))
                    if w == 0:
                        # Find screen width from window or default
                        screen_w = 375
                        tree = get_ui_tree(silent=True)
                        if tree:
                            for el in tree:
                                if el.get("role") == "Window":
                                    f = el.get("frame", {})
                                    screen_w = float(f.get("width", f.get("w", screen_w)))
                                    break
                        target_x = screen_w / 2
                        print(f"Tapping '{query}' (zero-width) at screen center {target_x}, {target_y}...", file=sys.stderr)
                    else:
                        print(f"Tapping '{query}' at {target_x}, {target_y}...", file=sys.stderr)
                except (ValueError, TypeError):
                    print(f"Tapping '{query}' at {target_x}, {target_y}...", file=sys.stderr)
            else:
                fail(ERR_ELEMENT_NOT_FOUND, f"Element '{query}' found but has no frame.")
        elif x is None or y is None:
             fail(ERR_ELEMENT_NOT_FOUND, f"Element '{query}' not found.", EXIT_ELEMENT_NOT_FOUND)

    # Fallback to coordinates if query failed or not provided
    if target_x is not None and target_y is not None:
        try:
            ix, iy = int(round(float(target_x))), int(round(float(target_y)))
            wda.tap(ix, iy)
            print(json.dumps({"status": "success", "action": "tap", "target": f"{ix},{iy}"}))
        except Exception as e:
            fail(ERR_COMMAND_FAILED, f"Tap failed: {e}")
    else:
        if not query and (x is None or y is None):
            fail(ERR_INVALID_ARGS, "Must provide query or coordinates.", EXIT_INVALID_ARGS)

def type_cmd(text: str, submit: bool = False):
    try:
        wda.type_text(text)
        if submit:
             wda.press_key("ENTER")
        print(json.dumps({"status": "success", "action": "type", "text": text, "submit": submit}))
    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Type failed: {e}")

def scroll_cmd(direction: str, until_visible: str = None, silent: bool = False):
    # Try to get screen dimensions from inspect
    tree = get_ui_tree(silent=True) # Silent to avoid polluting stdout on error
    w, h = None, None
    if tree:
        for el in tree:
            if el.get("role") == "Window":
                f = el.get("frame", {})
                if isinstance(f, dict):
                    try:
                        w = float(f.get("width", f.get("w", w or 375)))
                        h = float(f.get("height", f.get("h", h or 812)))
                    except (ValueError, TypeError):
                        pass
                if w and h:
                    break
    
    # Fallback if no window found or dimensions missing
    w = w or 375
    h = h or 812

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
        fail(ERR_INVALID_ARGS, f"Invalid direction: {direction}", EXIT_INVALID_ARGS)

    def perform_scroll():
        ixs, iys = int(round(start_x)), int(round(start_y))
        ixe, iye = int(round(end_x)), int(round(end_y))
        wda.swipe(ixs, iys, ixe, iye, 0.5)

    try:
        if until_visible:
            max_retries = 10
            # Check first before scrolling
            if find_element(until_visible, silent=True):
                 if not silent:
                     print(json.dumps({"status": "success", "action": "scroll", "found": until_visible}))
                 return

            for i in range(max_retries):
                # We can't easily print progress to stderr without confusing the model if it parses stderr.
                # But typically we want to be silent until success or failure.
                perform_scroll()
                time.sleep(1.0) # Wait for animation
                if find_element(until_visible, silent=True):
                    if not silent:
                        print(json.dumps({"status": "success", "action": "scroll", "found": until_visible}))
                    return
            
            fail(ERR_ELEMENT_NOT_FOUND, f"Element '{until_visible}' not found after scrolling.", EXIT_ELEMENT_NOT_FOUND)
        else:
            perform_scroll()
            if not silent:
                print(json.dumps({"status": "success", "action": "scroll", "direction": direction}))
    except Exception as e:
         fail(ERR_COMMAND_FAILED, f"Scroll failed: {e}")

def gesture_cmd(gesture_type: str, args: list):
    if gesture_type == "swipe":
        # Expect 4 numbers and optional duration. 
        # Can be in "x,y x,y" format or "x y x y" or "x y x y duration"
        flat_args = []
        for arg in args:
            flat_args.extend(arg.replace(',', ' ').split())

        duration = "0.5" # Default for reliable scrolling
        if len(flat_args) == 5:
            duration = flat_args.pop()

        if len(flat_args) != 4:
            fail(ERR_INVALID_ARGS, "Usage: gesture swipe start_x,start_y end_x,end_y [duration]", EXIT_INVALID_ARGS)

        try:
             # Validate numbers
             coords = [int(round(float(x))) for x in flat_args]
             wda.swipe(coords[0], coords[1], coords[2], coords[3], float(duration))
             print(json.dumps({"status": "success", "action": "gesture", "type": "swipe", "coords": coords, "duration": duration}))
        except ValueError:
             fail(ERR_INVALID_ARGS, "Invalid coordinates or duration for swipe.", EXIT_INVALID_ARGS)
        except Exception as e:
            fail(ERR_COMMAND_FAILED, f"Swipe failed: {e}")

    elif gesture_type == "pinch":
         fail(ERR_COMMAND_FAILED, "Pinch gesture not implemented.", EXIT_COMMAND_FAILED)
    else:
         fail(ERR_INVALID_ARGS, f"Unknown gesture: {gesture_type}", EXIT_INVALID_ARGS)
