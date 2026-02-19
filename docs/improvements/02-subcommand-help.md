# 02: Fix Subcommand Help

**Impact:** High — AI agents (and humans) cannot discover argument syntax.
**Effort:** Small
**Files:** `pippin/main.py`

## Problem

Lines 10-50 of `main.py` intercept `-h` / `--help` before argparse processes the subcommand:

```python
if "-h" in sys.argv or "--help" in sys.argv:
    print("Pippin: A CLI for iOS Automation")
    print("""...""")
    sys.exit(0)
```

This means `pippin tap --help`, `pippin inspect -h`, `pippin launch --help` all print the same top-level overview. The per-subcommand parsers have detailed argument definitions (e.g., `--interactive-only`, `--depth`, `--submit`, `--until-visible`) but they're completely invisible.

## Proposed Fix

Remove the manual help interception entirely and let argparse handle it natively.

### Changes to `main.py`

1. **Remove lines 10-50** (the `if "-h" in sys.argv` block).

2. **Change `add_help=False` to `add_help=True`** on the main parser (line 56), or remove the parameter entirely since `True` is the default.

3. **Remove the manual `parser.add_argument('-h', '--help', ...)` on line 57** — argparse handles this automatically.

4. **Customize the top-level description** to include the grouped command overview:

```python
DESCRIPTION = """\
Pippin: A Token-Efficient CLI for iOS Automation

Vision:
  inspect           Inspect UI hierarchy and return a simplified JSON tree
  screenshot        Capture the visual state for verification

Interaction:
  tap               Tap a UI element (by label or X Y coordinates)
  type              Input text into the currently focused field
  scroll            Scroll the screen
  gesture           Perform a specific gesture

System:
  launch            Launch an application
  stop              Terminate a running application
  relaunch          Stop and then start an application
  open              Open a URL scheme or Universal Link
  permission        Manage TCC (Privacy) permissions
  location          Simulate GPS coordinates

Verification:
  assert            Perform a quick boolean check on the UI state
  wait              Wait for an element to appear or disappear
  logs              Fetch the tail of the system log for the target app
  tree              List files in the app's sandbox containers

Utils:
  doctor            Check if all dependencies are installed
"""

parser = argparse.ArgumentParser(
    description=DESCRIPTION,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    usage="pippin [command] [options]",
)
```

### Result

After this change:

```
$ pippin --help          → Shows the grouped overview + global options
$ pippin tap --help      → Shows: "Tap a UI element" + args/flags for tap
$ pippin inspect --help  → Shows: --interactive-only, --all, --depth flags
$ pippin launch --help   → Shows: bundle_id, --clean, --args, --locale
```

### Also fix the `except SystemExit` block

Lines 137-143 have a `try/except SystemExit` that was a workaround for the broken help. With native help handling, this can be simplified:

```python
args = parser.parse_args()
```

No try/except needed — argparse will print help and exit cleanly on its own.

## Testing

- Verify `pippin -h` still shows the grouped overview.
- Verify `pippin <subcommand> -h` shows per-subcommand args.
- Verify that invalid arguments produce useful error messages (argparse does this by default).
