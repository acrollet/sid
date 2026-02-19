# 05: Multi-Simulator / Device Targeting

**Impact:** Medium — tool completely breaks with multiple simulators.
**Effort:** Small
**Files:** `pippin/main.py`, `pippin/utils/ui.py`, `pippin/utils/device.py` (new)

## Problem

When multiple simulators exist (common — most developers have several), `idb` fails with:

```
No udid provided and there are multiple companions to run against
dict_keys(['61B8F683-...', 'BB13ECAA-...'])
```

There's no `--udid` or `--device` flag anywhere in pippin. The tool uses `"booted"` for `simctl` commands but `idb` needs explicit targeting when multiple companions are registered.

## Proposed Changes

### 1. Add global `--device` flag

In `main.py`, add a global argument before the subparsers:

```python
parser.add_argument(
    "--device",
    help="Target simulator UDID. Defaults to the booted simulator. "
         "Use 'pippin doctor' to list available devices.",
    default=None,
)
```

### 2. Create `pippin/utils/device.py`

```python
import json
from pippin.utils.executor import execute_command

_target_udid = None

def set_target_device(udid: str):
    global _target_udid
    _target_udid = udid

def get_target_udid():
    """Return the target UDID, auto-selecting if only one is booted."""
    global _target_udid
    if _target_udid:
        return _target_udid

    # Get booted devices from simctl
    output = execute_command(
        ["xcrun", "simctl", "list", "devices", "booted", "--json"],
        capture_output=True,
    )
    devices = json.loads(output)
    booted = []
    for runtime, device_list in devices.get("devices", {}).items():
        for d in device_list:
            if d.get("state") == "Booted":
                booted.append(d["udid"])

    if len(booted) == 1:
        _target_udid = booted[0]
        return _target_udid
    elif len(booted) == 0:
        raise RuntimeError("No booted simulators found. Boot one with: xcrun simctl boot <udid>")
    else:
        raise RuntimeError(
            f"Multiple booted simulators found: {booted}. "
            f"Specify one with --device <udid>"
        )

def get_simctl_target():
    """Return the UDID or 'booted' for simctl commands."""
    try:
        return get_target_udid()
    except RuntimeError:
        return "booted"  # Let simctl figure it out / fail with its own error
```

### 3. Pass UDID to idb commands

In `ui.py`, update `ensure_idb_connected()` and all `idb` calls to use the target UDID:

```python
from pippin.utils.device import get_target_udid

def get_ui_tree(silent=False):
    udid = get_target_udid()
    # Use --udid flag with idb, or connect to specific device
    ensure_idb_connected(udid, silent=silent)
    output = execute_command(["idb", "ui", "describe-all", "--udid", udid], ...)
```

### 4. Enhance `doctor` to list devices

```
$ pippin doctor

Checking Pippin dependencies...
✅ idb found
✅ xcrun found

Simulators:
  BB13ECAA-...  iPhone 16 Pro    iOS 18.2  Booted  ← active
  61B8F683-...  iPhone 15        iOS 17.5  Booted

✨ Pippin is ready. Using: iPhone 16 Pro (BB13ECAA-...)
```

This helps the user (and AI) discover available devices and understand which one pippin will target.

### 5. Wire it up in `main.py`

```python
args = parser.parse_args()

if args.device:
    from pippin.utils.device import set_target_device
    set_target_device(args.device)

# ... dispatch to command
```

## Environment Variable Fallback

Also support `PIPPIN_DEVICE_UDID` env var so users can set it once per terminal session:

```bash
export PIPPIN_DEVICE_UDID=BB13ECAA-05F4-4E3B-A220-235BDBADFAB5
pippin inspect  # uses that device
```

## Testing

- Mock `simctl list devices` with 0, 1, and 2+ booted devices.
- Verify auto-selection works with exactly one booted device.
- Verify clear error with multiple booted devices and no `--device`.
- Verify `--device` override works.
