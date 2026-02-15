import argparse
import sys
from sid.commands.vision import inspect_cmd, screenshot_cmd
from sid.commands.interaction import tap_cmd, type_cmd, scroll_cmd, gesture_cmd
from sid.commands.system import launch_cmd, open_cmd, permission_cmd, location_cmd, network_cmd
from sid.commands.verification import assert_cmd, logs_cmd, tree_cmd

def main():
    parser = argparse.ArgumentParser(description="Sid: A Token-Efficient CLI for iOS Automation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Vision
    inspect_parser = subparsers.add_parser("inspect", help="Inspect UI hierarchy")
    inspect_parser.add_argument("--interactive-only", action="store_true", default=True, help="Filter for interactive elements (default)")
    inspect_parser.add_argument("--all", action="store_false", dest="interactive_only", help="Show all elements (disable interactive-only filter)")
    inspect_parser.add_argument("--depth", type=int, help="Limit depth")

    screenshot_parser = subparsers.add_parser("screenshot", help="Capture screenshot")
    screenshot_parser.add_argument("filename", help="Output filename")
    screenshot_parser.add_argument("--mask-text", action="store_true", help="Mask text (not implemented)")

    # Interaction
    tap_parser = subparsers.add_parser("tap", help="Tap an element")
    tap_parser.add_argument("query", nargs="?", help="Element query (ID or label)")
    tap_parser.add_argument("--x", type=int, help="X coordinate")
    tap_parser.add_argument("--y", type=int, help="Y coordinate")

    type_parser = subparsers.add_parser("type", help="Type text")
    type_parser.add_argument("text", help="Text to type")
    type_parser.add_argument("--submit", action="store_true", help="Press Enter after typing")

    scroll_parser = subparsers.add_parser("scroll", help="Scroll")
    scroll_parser.add_argument("direction", choices=["up", "down", "left", "right"], help="Direction")
    scroll_parser.add_argument("--until-visible", help="Scroll until element is visible")

    gesture_parser = subparsers.add_parser("gesture", help="Perform gesture")
    gesture_parser.add_argument("type", choices=["swipe", "pinch"], help="Gesture type")
    gesture_parser.add_argument("args", nargs=argparse.REMAINDER, help="Gesture arguments")

    # System
    launch_parser = subparsers.add_parser("launch", help="Launch app")
    launch_parser.add_argument("bundle_id", help="App Bundle ID")
    launch_parser.add_argument("--clean", action="store_true", help="Clean install simulation")
    launch_parser.add_argument("--args", help="Launch arguments")
    launch_parser.add_argument("--locale", help="Locale code")

    open_parser = subparsers.add_parser("open", help="Open URL")
    open_parser.add_argument("url", help="URL to open")

    perm_parser = subparsers.add_parser("permission", help="Manage permissions")
    perm_parser.add_argument("service", help="Service (camera, photos, etc)")
    perm_parser.add_argument("status", choices=["grant", "deny", "reset"], help="Status")

    loc_parser = subparsers.add_parser("location", help="Set location")
    loc_parser.add_argument("lat", help="Latitude")
    loc_parser.add_argument("lon", help="Longitude")

    net_parser = subparsers.add_parser("network", help="Network conditions")
    net_parser.add_argument("condition", help="Condition")

    # Verification
    assert_parser = subparsers.add_parser("assert", help="Assert UI state")
    assert_parser.add_argument("query", help="Element query")
    assert_parser.add_argument("state", help="Expected state (exists, visible, hidden, text=val)")

    logs_parser = subparsers.add_parser("logs", help="Fetch logs")
    logs_parser.add_argument("--crash-report", action="store_true", help="Check for crash")

    tree_parser = subparsers.add_parser("tree", help="List files")
    tree_parser.add_argument("directory", help="Directory (documents, caches, tmp)")

    args = parser.parse_args()

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

if __name__ == "__main__":
    main()
