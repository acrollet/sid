import sys
from pippin.utils import wda

def flatten_tree(nodes):
    flat_list = []
    if not isinstance(nodes, list):
        return flat_list
    for node in nodes:
        flat_list.append(node)
        if "nodes" in node:
            flat_list.extend(flatten_tree(node["nodes"]))
    return flat_list

from pippin.utils.device import get_target_udid

def get_ui_tree(silent=False):
    """Returns a flat list of UI elements from WDA."""
    try:
        udid = get_target_udid()
        wda.start_wda(udid)
        tree = wda.get_source_tree()
        if not tree:
            return []
        
        # WDA returns a root element, we wrap it in a list to match idb structure
        # or we just return the flattened tree of the root.
        nodes = tree.get("nodes", []) if "nodes" in tree else [tree]
        # Include the root node as well
        flat = flatten_tree([tree])
        return flat
    except Exception as e:
        if not silent:
            msg = f"Error fetching UI tree: {e}"
            print(msg, file=sys.stderr)
        return []

def get_ui_tree_hierarchical(silent=False):
    """Returns the raw nested tree from WDA, with each node's children intact."""
    try:
        udid = get_target_udid()
        wda.start_wda(udid)
        tree = wda.get_source_tree()
        if not tree:
            return []
        # Return as a list of root elements to match previous idb behavior
        return [tree]
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
    else:
        query_val = query

    def is_valid(el):
        """Check if element has valid dimensions for interaction."""
        f = el.get("frame")
        if not isinstance(f, dict):
             return False
        try:
            w = float(f.get("width", f.get("w", 0)))
            h = float(f.get("height", f.get("h", 0)))
            return w > 0 and h > 0
        except (ValueError, TypeError):
            return False

    def score_element(el):
        """Score element based on how likely it is to be the intended target."""
        score = 0
        role = (el.get("role") or el.get("type") or "").lower().replace("ax", "")
        
        # Prefer interactive roles
        if role in ["button", "cell", "textfield", "link", "switch"]:
            score += 10
        
        # Prefer elements with dimensions
        if is_valid(el):
            score += 20
            
        return score

    exact_id = []
    exact_label = []
    substring_label = []

    for el in elements:
        # Skip non-visible elements — they are off-screen and can't be tapped
        if el.get("visible") is False:
            continue

        # Filter by type if specified
        if element_type:
            role = (el.get("role") or el.get("type") or "").lower().replace("ax", "")
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
        elif not strict:
            if query_lower in label_lower:
                substring_label.append(el)
            else:
                # Keyword fallback: all query words (min 3 chars) must be in label
                words = [w for w in query_lower.split() if len(w) > 2]
                if words and all(w in label_lower for w in words):
                    substring_label.append(el)

    def pick_best(matches):
        if not matches:
            return None
        # Sort by score descending
        return sorted(matches, key=score_element, reverse=True)[0]

    # Return best match
    if exact_id:
        if len(exact_id) > 1 and not silent:
            print(f"WARN: {len(exact_id)} elements matched id '{query_val}', picking best.", file=sys.stderr)
        return pick_best(exact_id)

    if exact_label:
        if len(exact_label) > 1 and not silent:
            print(f"WARN: {len(exact_label)} elements matched label '{query_val}', picking best.", file=sys.stderr)
        return pick_best(exact_label)

    if substring_label:
        # Filter substring matches to those that at least have valid dimensions if possible
        valid_substring = [e for e in substring_label if is_valid(e)]
        if valid_substring:
             if len(valid_substring) > 1 and not silent:
                  print(f"WARN: {len(valid_substring)} valid elements contain '{query_val}', picking best.", file=sys.stderr)
             return pick_best(valid_substring)
        
        if len(substring_label) > 1 and not silent:
            print(f"WARN: {len(substring_label)} elements contain '{query_val}' in label, picking best.", file=sys.stderr)
        return pick_best(substring_label)

    return None

def is_onscreen(el):
    """Checks if an element's frame intersects with the device screen."""
    f = el.get("frame")
    if getattr(is_onscreen, "screen_w", None) is None:
        tree = get_ui_tree(silent=True)
        is_onscreen.screen_w = 375
        is_onscreen.screen_h = 812
        if tree:
            for node in tree:
                if node.get("role") in ["Window", "AXWindow", "AXApplication"]:
                    wf = node.get("frame", {})
                    try:
                        is_onscreen.screen_w = float(wf.get("width", wf.get("w", is_onscreen.screen_w)))
                        is_onscreen.screen_h = float(wf.get("height", wf.get("h", is_onscreen.screen_h)))
                    except:
                        pass
                    break

    if not isinstance(f, dict):
        return False
    try:
        x = float(f.get("x", 0))
        y = float(f.get("y", 0))
        w = float(f.get("width", f.get("w", 0)))
        h = float(f.get("height", f.get("h", 0)))
        
        if x + w <= 0 or x >= is_onscreen.screen_w:
            return False
        if y + h <= 0 or y >= is_onscreen.screen_h:
            return False
        return True
    except:
        return False

def get_center(frame):
    if isinstance(frame, dict):
        try:
            x = float(frame.get('x', 0))
            y = float(frame.get('y', 0))
            w = float(frame.get('width', frame.get('w', 0)))
            h = float(frame.get('height', frame.get('h', 0)))
            
            # If width or height is 0, we can't reliably tap the center of an "area"
            return x + w / 2, y + h / 2
        except (ValueError, TypeError):
            return None
    return None
