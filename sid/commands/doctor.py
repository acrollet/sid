import shutil
import sys
import os
import subprocess
from sid.utils.executor import execute_command

def _install_idb():
    print("\nAttempting to install idb dependencies...")
    
    if not shutil.which("brew"):
        print("❌ Homebrew (brew) is not installed. Please install it from https://brew.sh/ first.")
        return False

    try:
        print("1. Tapping facebook/fb...")
        subprocess.run(["brew", "tap", "facebook/fb"], check=True)
        
        print("2. Installing idb-companion...")
        subprocess.run(["brew", "install", "idb-companion"], check=True)
        
        print("3. Installing fb-idb (Python client)...")
        # If we are in a uv-managed environment, 'pip' might not be available as a module.
        # We try 'uv pip install' if uv is available, otherwise fallback to standard pip.
        try:
            if shutil.which("uv"):
                print(f"   (Using 'uv pip install' for {sys.executable})")
                subprocess.run(["uv", "pip", "install", "--python", sys.executable, "fb-idb"], check=True)
            else:
                subprocess.run([sys.executable, "-m", "pip", "install", "fb-idb"], check=True)
        except subprocess.CalledProcessError:
             # Last ditch effort: try just 'pip' with break-system-packages if on macOS
             cmd = ["pip", "install", "fb-idb"]
             if sys.platform == "darwin":
                 cmd.append("--break-system-packages")
             subprocess.run(cmd, check=True)
        
        print("\n✅ idb dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Installation failed: {e}")
        return False

def doctor_cmd():
    print("Checking Sid dependencies...\n")
    
    dependencies = {
        "idb": "Essential for UI inspection and advanced interactions.",
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

        if not path and bin_name == "idb":
            print(f"❌ {bin_name} NOT FOUND")
            choice = input(f"   Would you like to attempt to install {bin_name}? [y/N]: ").lower()
            if choice == 'y':
                if _install_idb():
                    path = shutil.which(bin_name)

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
            if bin_name != "idb" or (bin_name == "idb" and 'choice' in locals() and choice != 'y'):
                print(f"❌ {bin_name} NOT FOUND")
                print(f"   Hint: {description}")
            all_passed = False

    print("\nEnvironment Check:")
    try:
        targets = execute_command(["idb", "list-targets"], capture_output=True)
        if targets and "booted" in targets.lower():
            print("✅ iOS Simulator is currently booted.")
        else:
            print("⚠️  No booted iOS Simulator detected. Some commands may fail.")
    except Exception:
        print("❌ Could not communicate with idb.")
        print("   Hint: Ensure 'idb-companion' is running. If you have a booted simulator, try:")
        
        # Try to find a booted UDID to make the hint better
        try:
            targets = execute_command(["idb", "list-targets"], capture_output=True)
            booted_udid = None
            for line in targets.split("\n"):
                if "booted" in line.lower() and "no companion connected" in line.lower():
                    booted_udid = line.split("|")[1].strip()
                    break
            if booted_udid:
                print(f"         idb connect {booted_udid}")
            else:
                print("         idb connect [UDID]")
        except Exception:
            print("         idb connect [UDID]")
            
        all_passed = False

    if all_passed:
        print("\n✨ Sid is ready to go!")
    else:
        print("\n⚠️  Some dependencies are missing or misconfigured.")
        sys.exit(1)
