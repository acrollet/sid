import argparse
import sys
from pippin.commands.vision import inspect_cmd, screenshot_cmd
from pippin.commands.interaction import tap_cmd, type_cmd, scroll_cmd, gesture_cmd
from pippin.commands.system import launch_cmd, stop_cmd, relaunch_cmd, open_cmd, permission_cmd, location_cmd, network_cmd
from pippin.commands.verification import assert_cmd, logs_cmd, tree_cmd, wait_cmd
from pippin.commands.doctor import doctor_cmd

def main():
    DESCRIPTION = """\
Pippin: A CLI for iOS Automation

Vision:
  context           Get a composite context of the current state (Device, App, UI, etc).
  inspect           Inspect UI hierarchy and return a simplified JSON tree.
  screenshot        Capture the visual state for verification.

Interaction:
Pippin: A Token-Efficient CLI for iOS Automation

Overview:
  • Vision & Context:
    inspect [--flat]   View UI hierarchy (default: hierarchical, use --flat for flat list)
    context            Get comprehensive state (device, app, screen, UI, logs)
    screenshot <file>  Take a screenshot

  • Interaction:
    tap <query>        Tap an element by label/ID
    tap <x> <y>        Tap at coordinates
    type <text>        Type text into focused element
    scroll <dir>       Scroll (up/down/left/right)
    gesture <type> ... Perform gestures (swipe, etc.)

  • System:
    launch <bundleId>  Launch an app
    stop <bundleId>    Stop an app
    open <url>         Open a URL (deep link or web)
    home               Go to home screen

  • Verification:
    assert <query> <state>   Verify element state (exists/visible/text=...)
    wait <query>             Wait for element to appear

  • Device:
    doctor             Check environment and list devices

Options:
  --device <udid>    Target a specific simulator (defaults to booted)
"""

    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="pippin [options] [command] [args]", # Update usage to show options before command
    )
    parser.add_argument("--device", help="Target simulator UDID", default=None)

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Vision
    inspect_parser = subparsers.add_parser("inspect", help="Inspect UI hierarchy and return a simplified JSON tree.")
    inspect_parser.add_argument("--interactive-only", action="store_true", default=True, help="Filter out structural containers and keep actionable elements (Button, TextField, Cell, Switch, StaticText). Default: True")
    inspect_parser.add_argument("--all", action="store_false", dest="interactive_only", help="Show all elements, disabling the interactive-only filter.")
    inspect_parser.add_argument("--depth", type=int, help="Limit the hierarchy depth to save tokens. (Note: Partial support)")
    inspect_parser.add_argument("--flat", action="store_true", help="Return a flat list of elements instead of a hierarchical tree (Legacy mode).")

    screenshot_parser = subparsers.add_parser("screenshot", help="Capture the visual state for verification.")
    screenshot_parser.add_argument("filename", help="The output filename for the screenshot (e.g., screen.png).")
    screenshot_parser.add_argument("--mask-text", action="store_true", help="Redact text for privacy/security (Not Implemented).")

    # Interaction
    tap_parser = subparsers.add_parser("tap", help="Tap a UI element.")
    tap_parser.add_argument("args", nargs="*", help="The accessibility identifier, label text, or X Y coordinates.")
    tap_parser.add_argument("--x", type=int, help="Fallback X coordinate if query fails or is not provided.")
    tap_parser.add_argument("--y", type=int, help="Fallback Y coordinate if query fails or is not provided.")
    tap_parser.add_argument("--strict", action="store_true", help="Use strict matching (exact ID or label only, no substring).")

    type_parser = subparsers.add_parser("type", help="Input text into the currently focused field.")
    type_parser.add_argument("text", help="The text string to type.")
    type_parser.add_argument("--submit", action="store_true", help="Press 'Return/Enter' on the keyboard after typing.")

    scroll_parser = subparsers.add_parser("scroll", help="Scroll the screen.")
    scroll_parser.add_argument("direction", choices=["up", "down", "left", "right"], help="The direction to scroll.")
    scroll_parser.add_argument("--until-visible", help="Scroll repeatedly until the specified element (ID or label) becomes visible in the inspect tree.")

    gesture_parser = subparsers.add_parser("gesture", help="Perform a specific gesture.")
    gesture_parser.add_argument("type", choices=["swipe", "pinch"], help="The type of gesture to perform.")
    gesture_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the gesture (e.g., start_x,start_y end_x,end_y for swipe).")

    # System
    launch_parser = subparsers.add_parser("launch", help="Launch an application.")
    launch_parser.add_argument("bundle_id", nargs="?", help="The Bundle ID of the app to launch (e.g., com.example.app).")
    launch_parser.add_argument("--clean", action="store_true", help="Wipe the app container before launching to simulate a fresh install.")
    launch_parser.add_argument("--args", help="Launch arguments to pass to the app (e.g., '-TakingScreenshots YES').")
    launch_parser.add_argument("--locale", help="Launch the app in a specific language/locale (e.g., es-MX).")

    stop_parser = subparsers.add_parser("stop", help="Terminate a running application.")
    stop_parser.add_argument("bundle_id", nargs="?", help="The Bundle ID of the app to stop. Uses last launched app if omitted.")

    relaunch_parser = subparsers.add_parser("relaunch", help="Stop and then start an application.")
    relaunch_parser.add_argument("bundle_id", nargs="?", help="The Bundle ID of the app to relaunch. Uses last launched app if omitted.")
    relaunch_parser.add_argument("--clean", action="store_true", help="Wipe the app container before launching.")
    relaunch_parser.add_argument("--args", help="Launch arguments to pass to the app.")
    relaunch_parser.add_argument("--locale", help="Launch the app in a specific language/locale.")

    open_parser = subparsers.add_parser("open", help="Open a URL scheme or Universal Link.")
    open_parser.add_argument("url", help="The URL to open (e.g., myapp://settings).")

    perm_parser = subparsers.add_parser("permission", help="Manage TCC (Privacy) permissions.")
    perm_parser.add_argument("service", help="The service to modify (camera, photos, location, microphone, etc).")
    perm_parser.add_argument("status", choices=["grant", "deny", "reset"], help="The permission status to apply.")

    loc_parser = subparsers.add_parser("location", help="Simulate GPS coordinates.")
    loc_parser.add_argument("lat", help="Latitude.")
    loc_parser.add_argument("lon", help="Longitude.")

    net_parser = subparsers.add_parser("network", help="Simulate network conditions (Not Supported).")
    net_parser.add_argument("condition", help="The network condition to apply.")

    # Verification
    assert_parser = subparsers.add_parser("assert", help="Perform a quick boolean check on the UI state.")
    assert_parser.add_argument("query", help="The element identifier or label to check.")
    assert_parser.add_argument("state", help="The expected state: 'exists', 'visible', 'hidden', or 'text=value'.")
    assert_parser.add_argument("--strict", action="store_true", help="Use strict matching.")

    wait_parser = subparsers.add_parser("wait", help="Wait for an element to reach a certain state.")
    wait_parser.add_argument("query", help="The element identifier or label to wait for.")
    wait_parser.add_argument("--state", choices=["exists", "visible", "hidden"], default="visible", help="The state to wait for. Default: visible")
    wait_parser.add_argument("--timeout", type=float, default=10.0, help="Maximum time to wait in seconds. Default: 10.0")
    wait_parser.add_argument("--strict", action="store_true", help="Use strict matching.")

    logs_parser = subparsers.add_parser("logs", help="Fetch the tail of the system log for the target app.")
    logs_parser.add_argument("--crash-report", action="store_true", help="Check if a crash log was generated in the last session.")

    tree_parser = subparsers.add_parser("tree", help="List files in the app's sandbox containers.")
    tree_parser.add_argument("directory", help="The directory to list: 'documents', 'caches', or 'tmp'.")

    subparsers.add_parser("doctor", help="Check if all dependencies are installed.")
    
    # Context
    context_parser = subparsers.add_parser("context", help="Get a composite context of the current state (Device, App, UI, etc).")
    context_parser.add_argument("--include-logs", action="store_true", help="Include recent system logs.")
    context_parser.add_argument("--screenshot", help="Path to save a screenshot (e.g. screenshot.png).")
    context_parser.add_argument("--brief", action="store_true", help="Return only metadata, omit the full UI tree.")

    args = parser.parse_args()
    
    # Set global target device if provided
    if args.device:
        from pippin.utils.device import set_target_device
        set_target_device(args.device)

    # Dispatch commands
    if args.command == "inspect":
        inspect_cmd(interactive_only=args.interactive_only, depth=args.depth, flat=args.flat)
    elif args.command == "context":
        from pippin.commands.context import context_cmd
        context_cmd(include_logs=args.include_logs, screenshot_path=args.screenshot, brief=args.brief)
    elif args.command == "screenshot":
        screenshot_cmd(args.filename, mask_text=args.mask_text)
    elif args.command == "tap":
        query = None
        x, y = args.x, args.y
        if len(args.args) == 2:
            try:
                x, y = int(args.args[0]), int(args.args[1])
            except ValueError:
                query = " ".join(args.args)
        elif len(args.args) >= 1:
            query = " ".join(args.args)
        tap_cmd(query=query, x=x, y=y, strict=args.strict)
    elif args.command == "type":
        type_cmd(args.text, submit=args.submit)
    elif args.command == "scroll":
        scroll_cmd(args.direction, until_visible=args.until_visible)
    elif args.command == "gesture":
        gesture_cmd(args.type, args.args)
    elif args.command == "launch":
        launch_cmd(args.bundle_id, clean=args.clean, args=args.args, locale=args.locale)
    elif args.command == "stop":
        stop_cmd(args.bundle_id)
    elif args.command == "relaunch":
        relaunch_cmd(args.bundle_id, clean=args.clean, args=args.args, locale=args.locale)
    elif args.command == "open":
        open_cmd(args.url)
    elif args.command == "permission":
        permission_cmd(args.service, args.status)
    elif args.command == "location":
        location_cmd(args.lat, args.lon)
    elif args.command == "network":
        network_cmd(args.condition)
    elif args.command == "assert":
        assert_cmd(args.query, args.state, strict=args.strict)
    elif args.command == "wait":
        wait_cmd(args.query, timeout=args.timeout, state=args.state, strict=args.strict)
    elif args.command == "logs":
        logs_cmd(crash_report=args.crash_report)
    elif args.command == "tree":
        tree_cmd(args.directory)
    elif args.command == "doctor":
        doctor_cmd()

if __name__ == "__main__":
    main()
