import shutil
import sys
import os
import subprocess
import json
from pippin.utils.executor import execute_command
from pippin.utils import wda

def doctor_cmd():
    print("Checking Pippin dependencies...\n")
    
    dependencies = {
        "xcrun": "Essential for simulator control (simctl).",
    }
    
    all_passed = True
    
    for bin_name, description in dependencies.items():
        path = shutil.which(bin_name)
        
        # If not in PATH, check the same directory as the current python (common for venvs)
        if not path:
            local_bin = os.path.join(os.path.dirname(sys.executable), bin_name)
            if os.path.exists(local_bin):
                path = local_bin

        if path:
            print(f"✅ {bin_name} found at: {path}")
            try:
                if bin_name == "xcrun":
                    output = execute_command(["xcrun", "simctl", "help"], capture_output=True)
                    version = output.split("\n")[0] if output else "Unknown"
                else:
                    version = execute_command([bin_name, "--version"], capture_output=True)
                print(f"   Version: {version.strip()}")
            except Exception:
                pass
        else:
            print(f"❌ {bin_name} NOT FOUND")
            print(f"   Hint: {description}")
            all_passed = False

    print("\nWebDriverAgent Check:")
    has_wda = wda._get_wda_bundle_path() is not None
    if has_wda:
        print("✅ WebDriverAgent bundle found.")
    else:
        print("❌ WebDriverAgent bundle NOT FOUND.")
        try:
            choice = input("   Would you like to download and install WebDriverAgent? [y/N]: ").lower()
        except (EOFError, KeyboardInterrupt):
            choice = 'n'
            
        if choice == 'y':
            try:
                wda.install_wda()
                print("✅ WebDriverAgent installed successfully.")
                has_wda = True
            except Exception as e:
                print(f"❌ Failed to install WebDriverAgent: {e}")
                all_passed = False
        else:
            all_passed = False

    print("\nEnvironment Check:")
    try:
        from pippin.utils.device import get_target_udid
        # We catch explicit exit from get_target_udid if it fails (ambiguous) 
        # but here we want to list devices first.
        
        # Manually list devices to show status
        output = execute_command(["xcrun", "simctl", "list", "devices", "booted", "--json"], capture_output=True)
        devices = json.loads(output)
        
        booted_list = []
        for runtime, dev_list in devices.get("devices", {}).items():
            for d in dev_list:
                if d.get("state") == "Booted":
                    d["runtime"] = runtime.split(".")[-1]
                    booted_list.append(d)

        if not booted_list:
            print("❌ No booted simulators found.")
            print("   Hint: Launch a simulator via Xcode or 'xcrun simctl boot <UDID>'")
        else:
            print(f"✅ Found {len(booted_list)} booted simulator(s):")
            
            # Try to resolve target to mark it
            current_target = None
            try:
                import io
                old_stderr = sys.stderr
                sys.stderr = io.StringIO()  # Suppress fail() output from get_target_udid
                try:
                    current_target = get_target_udid()
                finally:
                    sys.stderr = old_stderr
            except SystemExit:
                pass # Ambiguous or none, we'll mark none
            except Exception:
                pass

            for d in booted_list:
                marker = " "
                if current_target and d["udid"] == current_target:
                    marker = "→"
                
                print(f"   {marker} {d['name']} ({d['udid']}) - {d['runtime']}")
                
                # Check WDA status if it's the active one
                if current_target and d["udid"] == current_target and has_wda:
                    if wda.ensure_wda_running():
                        print("      ✅ WebDriverAgent is running.")
                    else:
                        print("      ⚠️  WebDriverAgent is not running. It will start automatically when needed.")
            
            if len(booted_list) > 1 and not current_target:
                print("\n   ⚠️  Multiple simulators booted. Target is ambiguous.")
                print("      Use --device <UDID> or set PIPPIN_DEVICE_UDID to select one.")
            elif current_target:
                print(f"\n   Targeting: {current_target}")

    except Exception as e:
        print(f"❌ Error checking simulators: {e}")
        all_passed = False

    if all_passed:
        print("\n✨ Pippin is ready to go!")
    else:
        print("\n⚠️  Some dependencies are missing or misconfigured.")
        sys.exit(1)
