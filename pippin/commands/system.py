import sys
import os
import shlex
import json
from pippin.utils.executor import execute_command
from pippin.utils.errors import (
    fail, EXIT_COMMAND_FAILED, EXIT_APP_NOT_RUNNING, EXIT_INVALID_ARGS,
    ERR_NO_TARGET_APP, ERR_COMMAND_FAILED
)
from pippin.utils.device import get_simctl_target, get_target_udid
from pippin.utils.state import get_last_bundle_id, set_last_bundle_id

def _get_app_container(bundle_id):
    try:
        udid = get_simctl_target()
        return execute_command(["xcrun", "simctl", "get_app_container", udid, bundle_id, "data"])
    except Exception as e:
        print(f"WARN: Error getting app container for {bundle_id}: {e}", file=sys.stderr)
        return None

def launch_cmd(bundle_id: str, clean: bool = False, args: str = None, locale: str = None):
    if not bundle_id:
        bundle_id = get_last_bundle_id()
    
    if not bundle_id:
        fail(ERR_NO_TARGET_APP, "Could not determine target app. Run 'pippin launch' first or provide a bundle ID.", EXIT_INVALID_ARGS)

    udid = get_simctl_target()

    if clean:
        print(f"Terminating and cleaning {bundle_id}...", file=sys.stderr)
        try:
            execute_command(["xcrun", "simctl", "terminate", udid, bundle_id], check=False)
            container = _get_app_container(bundle_id)
            if container:
                # Remove contents. Quote container path to be safe.
                execute_command(["sh", "-c", f"rm -rf \"{container}\"/*"])
        except Exception as e:
            print(f"WARN: Error cleaning app: {e}", file=sys.stderr)

    cmd = ["xcrun", "simctl", "launch", udid, bundle_id]
    if locale:
        # Pass locale arguments.
        # -AppleLanguages (en) -AppleLocale en_US
        cmd.extend(["-AppleLanguages", f"({locale})", "-AppleLocale", locale])
    if args:
        try:
            cmd.extend(shlex.split(args))
        except ValueError:
            cmd.append(args)

    try:
        execute_command(cmd)
        print(json.dumps({"status": "success", "action": "launch", "bundle_id": bundle_id}))
        set_last_bundle_id(bundle_id)
    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Error launching app: {e}")

def stop_cmd(bundle_id: str = None):
    if not bundle_id:
        bundle_id = get_last_bundle_id()
    
    if not bundle_id:
        fail(ERR_NO_TARGET_APP, "Could not determine target app. Run 'pippin launch' first or provide a bundle ID.", EXIT_INVALID_ARGS)

    try:
        udid = get_simctl_target()
        execute_command(["xcrun", "simctl", "terminate", udid, bundle_id])
        print(json.dumps({"status": "success", "action": "stop", "bundle_id": bundle_id}))
    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Error stopping app: {e}")

def relaunch_cmd(bundle_id: str = None, clean: bool = False, args: str = None, locale: str = None):
    # Relaunch reuses stop and launch, which handle their own errors/output.
    # To avoid double JSON output, we might want to silence them or just let them be.
    # For now, let's just use them as is, but we need to resolve bundle_id first to pass it consistently.
    
    if not bundle_id:
        bundle_id = get_last_bundle_id()
    
    if not bundle_id:
        fail(ERR_NO_TARGET_APP, "Could not determine target app.", EXIT_INVALID_ARGS)

    # We manually call implementation to control output if needed, or just let them run.
    # Calling stop logic directly to avoid double success message if we want a single "relaunch" message.
    udid = get_simctl_target()
    try:
        execute_command(["xcrun", "simctl", "terminate", udid, bundle_id], check=False)
    except Exception:
        pass
        
    launch_cmd(bundle_id, clean=clean, args=args, locale=locale)

def open_cmd(url: str):
    try:
        udid = get_simctl_target()
        execute_command(["xcrun", "simctl", "openurl", udid, url])
        print(json.dumps({"status": "success", "action": "open", "url": url}))
    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Error opening URL: {e}")

def permission_cmd(service: str, status: str):
    bundle_id = None
    bundle_id = get_last_bundle_id()

    if not bundle_id:
        fail(ERR_NO_TARGET_APP, "Could not determine target app. Run 'pippin launch' first.", EXIT_INVALID_ARGS)

    try:
        udid = get_simctl_target()
        execute_command(["xcrun", "simctl", "privacy", udid, status, service, bundle_id])
        print(json.dumps({"status": "success", "action": "permission", "service": service, "status": status, "bundle_id": bundle_id}))
    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Error setting permission: {e}")

def location_cmd(lat: str, lon: str):
    try:
        # Try idb first
        # idb set-location --udid ...
        udid = get_target_udid() 
        execute_command(["idb", "set-location", "--udid", udid, lat, lon])
        print(json.dumps({"status": "success", "action": "location", "lat": lat, "lon": lon}))
    except Exception as e:
        fail(ERR_COMMAND_FAILED, f"Error setting location: {e}")

def network_cmd(condition: str):
    fail(ERR_COMMAND_FAILED, "Network conditioning is not supported directly by this tool.")
