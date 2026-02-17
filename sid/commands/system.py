import sys
import os
import shlex
from sid.utils.executor import execute_command

STATE_FILE = "/tmp/sid_last_bundle_id"

def _get_app_container(bundle_id):
    try:
        return execute_command(["xcrun", "simctl", "get_app_container", "booted", bundle_id, "data"])
    except Exception as e:
        print(f"Error getting app container for {bundle_id}: {e}", file=sys.stderr)
        return None

def launch_cmd(bundle_id: str, clean: bool = False, args: str = None, locale: str = None):
    if not bundle_id:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    bundle_id = f.read().strip()
            except IOError:
                pass
    
    if not bundle_id:
        print("ERR_NO_TARGET_APP: Could not determine target app. Run 'sid launch' first or provide a bundle ID.", file=sys.stderr)
        return

    if clean:
        print(f"Terminating and cleaning {bundle_id}...")
        try:
            execute_command(["xcrun", "simctl", "terminate", "booted", bundle_id], check=False)
            container = _get_app_container(bundle_id)
            if container:
                # Remove contents. Quote container path to be safe.
                execute_command(["sh", "-c", f"rm -rf \"{container}\"/*"])
        except Exception as e:
            print(f"Error cleaning app: {e}", file=sys.stderr)

    cmd = ["xcrun", "simctl", "launch", "booted", bundle_id]
    if locale:
        # Pass locale arguments.
        # -AppleLanguages (en) -AppleLocale en_US
        cmd.extend(["-AppleLanguages", f"({locale})", "-AppleLocale", locale])
    if args:
        try:
            cmd.extend(shlex.split(args))
        except:
            cmd.append(args)

    try:
        execute_command(cmd)
        print(f"Launched {bundle_id}")
        try:
            with open(STATE_FILE, "w") as f:
                f.write(bundle_id)
        except IOError:
            pass # Ignore if can't write state
    except Exception as e:
        print(f"Error launching app: {e}", file=sys.stderr)

def stop_cmd(bundle_id: str = None):
    if not bundle_id:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    bundle_id = f.read().strip()
            except IOError:
                pass
    
    if not bundle_id:
        print("ERR_NO_TARGET_APP: Could not determine target app. Run 'sid launch' first or provide a bundle ID.", file=sys.stderr)
        return

    try:
        execute_command(["xcrun", "simctl", "terminate", "booted", bundle_id])
        print(f"Stopped {bundle_id}")
    except Exception as e:
        print(f"Error stopping app: {e}", file=sys.stderr)

def relaunch_cmd(bundle_id: str = None, clean: bool = False, args: str = None, locale: str = None):
    if not bundle_id:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    bundle_id = f.read().strip()
            except IOError:
                pass
    
    if not bundle_id:
        print("ERR_NO_TARGET_APP: Could not determine target app. Run 'sid launch' first or provide a bundle ID.", file=sys.stderr)
        return

    stop_cmd(bundle_id)
    launch_cmd(bundle_id, clean=clean, args=args, locale=locale)

def open_cmd(url: str):
    try:
        execute_command(["xcrun", "simctl", "openurl", "booted", url])
        print(f"Opened {url}")
    except Exception as e:
        print(f"Error opening URL: {e}", file=sys.stderr)

def permission_cmd(service: str, status: str):
    bundle_id = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                bundle_id = f.read().strip()
        except IOError:
            pass

    if not bundle_id:
        print("ERR_NO_TARGET_APP: Could not determine target app. Run 'sid launch' first.", file=sys.stderr)
        return

    try:
        execute_command(["xcrun", "simctl", "privacy", "booted", status, service, bundle_id])
        print(f"Permission {service} {status} for {bundle_id}")
    except Exception as e:
        print(f"Error setting permission: {e}", file=sys.stderr)

def location_cmd(lat: str, lon: str):
    try:
        # Try idb first
        execute_command(["idb", "set-location", lat, lon])
        print(f"Location set to {lat}, {lon}")
    except Exception:
        print(f"Error setting location via idb. Fallback not implemented.", file=sys.stderr)

def network_cmd(condition: str):
    print(f"Network conditioning to '{condition}' is not supported directly by this tool.", file=sys.stderr)
