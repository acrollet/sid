# 06: Smarter Element Matching

**Impact:** Medium — reduces "tapped the wrong thing" failures.
**Effort:** Medium
**Files:** `pippin/utils/ui.py`

## Problem

`find_element()` in `ui.py:69-86` has two matching strategies:

1. **Exact match on AXIdentifier** — good, but many elements lack identifiers.
2. **Substring match on AXLabel** — returns the *first* element containing the query.

The substring match is fragile. `pippin tap "General"` will match whichever of these comes first in the flat list:
- "General" (the cell we want)
- "General Settings" (a different cell)
- "In General, ..." (a description label)

The AI agent has no way to know it tapped the wrong element.

## Proposed Changes

### 1. Tiered matching with scoring

Replace the current two-pass approach with a ranked match:

```python
def find_element(query: str, silent=False, strict=False):
    elements = get_ui_tree(silent=silent)
    if not elements:
        return None

    query_lower = query.lower()
    exact_id = []
    exact_label = []
    substring_label = []

    for el in elements:
        # Tier 1: Exact accessibility identifier
        if el.get("AXIdentifier") == query:
            exact_id.append(el)

        label = (el.get("AXLabel") or "").lower()

        # Tier 2: Exact label match (case-insensitive)
        if label == query_lower:
            exact_label.append(el)

        # Tier 3: Substring match (skip in strict mode)
        elif not strict and query_lower in label:
            substring_label.append(el)

    # Return best match
    if exact_id:
        if len(exact_id) > 1 and not silent:
            print(f"WARN: {len(exact_id)} elements matched id '{query}', using first.", file=sys.stderr)
        return exact_id[0]

    if exact_label:
        if len(exact_label) > 1 and not silent:
            print(f"WARN: {len(exact_label)} elements matched label '{query}', using first.", file=sys.stderr)
        return exact_label[0]

    if substring_label:
        if len(substring_label) > 1 and not silent:
            print(f"WARN: {len(substring_label)} elements contain '{query}' in label, using first. "
                  f"Matches: {[e.get('AXLabel') for e in substring_label[:5]]}", file=sys.stderr)
        return substring_label[0]

    return None
```

### 2. Add `--strict` flag to `tap` and `assert`

```
pippin tap "General" --strict      # Only exact ID or exact label match
pippin tap "General"               # Current behavior (substring fallback)
```

### 3. Ambiguity reporting

When multiple elements match, include all matches in the warning so the AI can refine:

```
WARN: 3 elements contain 'General' in label, using first.
Matches: ['General', 'General Settings', 'General Information']
Tapped at 187, 340
```

The AI sees this warning on stderr and can decide whether to retry with a more specific query.

### 4. Support type-qualified queries

Allow `type:label` syntax to disambiguate:

```
pippin tap "Cell:General"           # Only match cells labeled "General"
pippin tap "Button:Cancel"          # Only match buttons labeled "Cancel"
```

Implementation in `find_element`:

```python
# Check for type:label syntax
element_type = None
if ":" in query and not query.startswith("http"):
    element_type, query = query.split(":", 1)
    element_type = element_type.lower()

# ... then filter by type during matching:
if element_type:
    role = (el.get("role") or "").lower().replace("ax", "")
    if role != element_type:
        continue
```

### 5. Index-based fallback

When inspect shows numbered elements, allow tapping by index:

```
pippin tap --index 3    # Tap the 3rd interactive element on screen
```

This is a last resort but useful when labels are ambiguous or missing.

## Testing

- Test exact ID match takes priority over substring label match.
- Test exact label match takes priority over substring.
- Test `--strict` rejects substring matches.
- Test ambiguity warning lists all matches.
- Test `type:label` syntax filters by element type.
- Test that the warning count is correct.
