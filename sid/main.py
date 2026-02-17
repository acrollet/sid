import argparse
import sys
from sid.commands.vision import inspect_cmd, screenshot_cmd
from sid.commands.interaction import tap_cmd, type_cmd, scroll_cmd, gesture_cmd
from sid.commands.system import launch_cmd, open_cmd, permission_cmd, location_cmd, network_cmd
from sid.commands.verification import assert_cmd, logs_cmd, tree_cmd
from sid.commands.doctor import doctor_cmd

def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print("Sid: A CLI for iOS Automation")
        print("""
Vision:
  inspect           Inspect UI hierarchy and return a simplified JSON tree.
  screenshot        Capture the visual state for verification.

Interaction:
  tap               Tap a UI element.
  type              Input text into the currently focused field.
  scroll            Scroll the screen.
  gesture           Perform a specific gesture.

System:
  launch            Launch an application.
  open              Open a URL scheme or Universal Link.
  permission        Manage TCC (Privacy) permissions.
  location          Simulate GPS coordinates.
  network           Simulate network conditions (Not Supported).

Verification:
  assert            Perform a quick boolean check on the UI state.
  logs              Fetch the tail of the system log for the target app.
  tree              List files in the app's sandbox containers.

Utils:
  doctor            Check if all dependencies (idb, xcrun) are installed.

Options:
  -h, --help        Show this help message

Examples:
  sid launch com.apple.Preferences --clean
  sid inspect
  sid tap "Settings"
  sid assert "General" visible
""")
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="Sid: A CLI for iOS Automation",
        usage="sid [command] [options]",
        add_help=False
    )
    parser.add_argument('-h', '--help', action='store_true')

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Vision
    inspect_parser = subparsers.add_parser("inspect", help="Inspect UI hierarchy and return a simplified JSON tree.")
    inspect_parser.add_argument("--interactive-only", action="store_true", default=True, help="Filter out structural containers and keep actionable elements (Button, TextField, Cell, Switch, StaticText). Default: True")
    inspect_parser.add_argument("--all", action="store_false", dest="interactive_only", help="Show all elements, disabling the interactive-only filter.")
    inspect_parser.add_argument("--depth", type=int, help="Limit the hierarchy depth to save tokens. (Note: Partial support)")

    screenshot_parser = subparsers.add_parser("screenshot", help="Capture the visual state for verification.")
    screenshot_parser.add_argument("filename", help="The output filename for the screenshot (e.g., screen.png).")
    screenshot_parser.add_argument("--mask-text", action="store_true", help="Redact text for privacy/security (Not Implemented).")

    # Interaction
    tap_parser = subparsers.add_parser("tap", help="Tap a UI element.")
    tap_parser.add_argument("query", nargs="?", help="The accessibility identifier or label text to match (fuzzy match).")
    tap_parser.add_argument("--x", type=int, help="Fallback X coordinate if query fails or is not provided.")
    tap_parser.add_argument("--y", type=int, help="Fallback Y coordinate if query fails or is not provided.")

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
    launch_parser.add_argument("bundle_id", help="The Bundle ID of the app to launch (e.g., com.example.app).")
    launch_parser.add_argument("--clean", action="store_true", help="Wipe the app container before launching to simulate a fresh install.")
    launch_parser.add_argument("--args", help="Launch arguments to pass to the app (e.g., '-TakingScreenshots YES').")
    launch_parser.add_argument("--locale", help="Launch the app in a specific language/locale (e.g., es-MX).")

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

    logs_parser = subparsers.add_parser("logs", help="Fetch the tail of the system log for the target app.")
    logs_parser.add_argument("--crash-report", action="store_true", help="Check if a crash log was generated in the last session.")

    tree_parser = subparsers.add_parser("tree", help="List files in the app's sandbox containers.")
    tree_parser.add_argument("directory", help="The directory to list: 'documents', 'caches', or 'tmp'.")

    subparsers.add_parser("doctor", help="Check if all dependencies are installed.")

    try:
        args = parser.parse_args()
    except SystemExit:
        if '-h' in sys.argv or '--help' in sys.argv:
            # This shouldn't be reached if we exit early, but as a safety:
            sys.exit(0)
        raise

    if args.command == "inspect":
        inspect_cmd(interactive_only=args.interactive_only, depth=args.depth)
    elif args.command == "screenshot":
        screenshot_cmd(args.filename, mask_text=args.mask_text)
    elif args.command == "tap":
        tap_cmd(query=args.query, x=args.x, y=args.y)
    elif args.command == "type":
        type_cmd(args.text, submit=args.submit)
    elif args.command == "scroll":
        scroll_cmd(args.direction, until_visible=args.until_visible)
    elif args.command == "gesture":
        gesture_cmd(args.type, args.args)
    elif args.command == "launch":
        launch_cmd(args.bundle_id, clean=args.clean, args=args.args, locale=args.locale)
    elif args.command == "open":
        open_cmd(args.url)
    elif args.command == "permission":
        permission_cmd(args.service, args.status)
    elif args.command == "location":
        location_cmd(args.lat, args.lon)
    elif args.command == "network":
        network_cmd(args.condition)
    elif args.command == "assert":
        assert_cmd(args.query, args.state)
    elif args.command == "logs":
        logs_cmd(crash_report=args.crash_report)
    elif args.command == "tree":
        tree_cmd(args.directory)
    elif args.command == "doctor":
        doctor_cmd()

if __name__ == "__main__":
    main()
