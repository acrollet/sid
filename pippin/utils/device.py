import os
import json
from pippin.utils.executor import execute_command
from pippin.utils.errors import fail, EXIT_INVALID_ARGS, ERR_INVALID_ARGS

_target_udid = None

def set_target_device(udid: str):
    global _target_udid
    _target_udid = udid

def get_target_udid():
    """Return the target UDID, auto-selecting if only one is booted."""
    global _target_udid
    if _target_udid:
        return _target_udid
    
    # Check env var
    env_udid = os.environ.get("PIPPIN_DEVICE_UDID")
    if env_udid:
        _target_udid = env_udid
        return _target_udid

    # Get booted devices from simctl
    try:
        output = execute_command(
            ["xcrun", "simctl", "list", "devices", "booted", "--json"],
            capture_output=True,
        )
    except Exception as e:
        fail("ERR_SIMCTL_LIST", f"Failed to list devices: {e}", EXIT_INVALID_ARGS)

    if not output:
        # Should ideally not happen if command succeeded but returned empty
        return "booted"

    try:
        devices = json.loads(output)
    except json.JSONDecodeError:
        return "booted"

    booted = []
    for runtime, device_list in devices.get("devices", {}).items():
        for d in device_list:
            if d.get("state") == "Booted":
                booted.append(d["udid"])

    if len(booted) == 1:
        _target_udid = booted[0]
        return _target_udid
    elif len(booted) == 0:
        fail(ERR_INVALID_ARGS, "No booted simulators found. Boot one with: xcrun simctl boot <udid>", EXIT_INVALID_ARGS)
    else:
        fail(ERR_INVALID_ARGS, f"Multiple booted simulators found: {booted}. Specify one with --device <udid> or PIPPIN_DEVICE_UDID.", EXIT_INVALID_ARGS)

def get_simctl_target():
    """Return the UDID or 'booted' for simctl commands."""
    try:
        return get_target_udid()
    except SystemExit:
        # If get_target_udid fails (e.g. multiple booted), we assume the caller
        # might want to handle it or we just default to "booted" if permissible?
        # Actually, get_target_udid calls fail() which exits.
        # So we don't need to catch here unless we want to avoid exiting.
        # But for simctl, "booted" is ambiguous if multiple are booted.
        # So strict mode is better.
        raise
