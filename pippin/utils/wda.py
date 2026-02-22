import json
import os
import subprocess
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

WDA_URL = "http://localhost:8100"
_session_id = None

def _wda_request(method, path, body=None, parse_json=True):
    url = f"{WDA_URL}{path}"
    req = urllib.request.Request(url, method=method)
    if body is not None:
        req.data = json.dumps(body).encode('utf-8')
        req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode('utf-8')
            if parse_json:
                if resp_body:
                    return json.loads(resp_body)
                return {}
            return resp_body
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise Exception(f"WDA Session Stale or Endpoint Not Found: {url}")
        raise Exception(f"WDA Request Failed: {e.code} - {e.read().decode('utf-8')}")
    except urllib.error.URLError as e:
        raise Exception(f"WDA Connection Failed: {e}")

def get_session():
    global _session_id
    if _session_id:
        return _session_id

    try:
        resp = _wda_request("POST", "/session", {"capabilities": {}})
        _session_id = resp.get("sessionId") or resp.get("value", {}).get("sessionId")
        return _session_id
    except Exception as e:
        raise e

def _with_session(func):
    def wrapper(*args, **kwargs):
        global _session_id
        try:
            get_session()
            return func(*args, **kwargs)
        except Exception as e:
            if "WDA Session Stale" in str(e):
                _session_id = None
                get_session()
                return func(*args, **kwargs)
            raise e
    return wrapper

def ensure_wda_running():
    try:
        resp = _wda_request("GET", "/status")
        return resp.get("value", {}).get("ready", False) or resp.get("ready", False)
    except Exception:
        return False

@_with_session
def get_source_tree():
    resp_body = _wda_request("GET", f"/session/{_session_id}/source", parse_json=False)
    try:
        try:
            data = json.loads(resp_body)
            xml_str = data.get("value", resp_body)
        except json.JSONDecodeError:
            xml_str = resp_body
            
        root = ET.fromstring(xml_str)
        return _xml_to_element(root)
    except Exception as e:
        raise Exception(f"Failed to parse source tree: {e}")

def _xml_to_element(node):
    el = {}
    
    node_type = node.get("type", "")
    if node_type:
        el["role"] = node_type.replace("XCUIElementType", "")
    else:
        tag = node.tag.split('}')[-1] if '}' in node.tag else node.tag
        if tag == "AppiumAUT":
            el["role"] = "application"
        else:
            el["role"] = tag.replace("XCUIElementType", "")

    if node.get("name"):
        el["AXIdentifier"] = node.get("name")
    if node.get("label"):
        el["AXLabel"] = node.get("label")
    if node.get("value"):
        el["AXValue"] = node.get("value")

    if node.get("visible") == "false":
        el["visible"] = False

    try:
        x = float(node.get("x", 0))
        y = float(node.get("y", 0))
        width = float(node.get("width", 0))
        height = float(node.get("height", 0))
        if "x" in node.attrib and "y" in node.attrib:
            el["frame"] = {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "w": width,
                "h": height
            }
    except ValueError:
        pass
    
    children = []
    for child in node:
        children.append(_xml_to_element(child))
    if children:
        el["nodes"] = children

    return el

@_with_session
def tap(x, y):
    _wda_request("POST", f"/session/{_session_id}/actions", {
        "actions": [{
            "type": "pointer",
            "id": "finger1",
            "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0, "x": x, "y": y},
                {"type": "pointerDown", "button": 0},
                {"type": "pause", "duration": 50},
                {"type": "pointerUp", "button": 0}
            ]
        }]
    })

@_with_session
def type_text(text):
    _wda_request("POST", f"/session/{_session_id}/wda/keys", {"value": list(text)})

@_with_session
def press_key(key):
    if key.upper() == "ENTER":
        _wda_request("POST", f"/session/{_session_id}/wda/keys", {"value": ["\\n"]})
    else:
        _wda_request("POST", f"/session/{_session_id}/wda/keys", {"value": [key]})

@_with_session
def swipe(x1, y1, x2, y2, duration):
    # Use W3C Actions instead of dragfromtoforduration to produce a scroll
    # gesture rather than a drag (which would drag links/elements).
    dur_ms = int(float(duration) * 1000)
    _wda_request("POST", f"/session/{_session_id}/actions", {
        "actions": [{
            "type": "pointer",
            "id": "finger1",
            "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0, "x": int(x1), "y": int(y1)},
                {"type": "pointerDown", "button": 0},
                {"type": "pointerMove", "duration": dur_ms, "x": int(x2), "y": int(y2)},
                {"type": "pointerUp", "button": 0}
            ]
        }]
    })

def _get_wda_bundle_path():
    wda_dir = Path.home() / ".pippin" / "wda"
    if wda_dir.exists():
        apps = list(wda_dir.glob("*.app"))
        if apps:
            return apps[0]
    return None

def install_wda():
    import tempfile
    import zipfile
    
    wda_dir = Path.home() / ".pippin" / "wda"
    if _get_wda_bundle_path():
        return
        
    wda_dir.mkdir(parents=True, exist_ok=True)
    
    import platform
    arch = platform.machine()
    asset_name = "WebDriverAgentRunner-Build-Sim-arm64.zip" if arch == "arm64" else "WebDriverAgentRunner-Build-Sim-x86_64.zip"

    # Fetch latest release API from GitHub
    print("Fetching WDA releases...")
    req = urllib.request.Request("https://api.github.com/repos/appium/WebDriverAgent/releases/latest")
    with urllib.request.urlopen(req) as response:
        release_info = json.loads(response.read().decode('utf-8'))
        
    download_url = None
    for asset in release_info.get("assets", []):
        if asset.get("name") == asset_name:
            download_url = asset.get("browser_download_url")
            break
            
    if not download_url:
        raise Exception(f"Could not find {asset_name} in the latest WDA release.")
        
    print(f"Downloading {asset_name}...")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        urllib.request.urlretrieve(download_url, tmp.name)
        
        print("Extracting...")
        with zipfile.ZipFile(tmp.name, 'r') as zip_ref:
            zip_ref.extractall(wda_dir)
            
        os.unlink(tmp.name)
        
    app_path = _get_wda_bundle_path()
    
    # Try to install if we can resolve UDID
    try:
        from pippin.utils.device import get_target_udid
        udid = get_target_udid()
        print(f"Installing WDA to {udid}...")
        subprocess.run(["xcrun", "simctl", "install", udid, str(app_path)], check=True)
    except Exception as e:
        # It's fine if this fails during install_wda, user might not have a booted simulator.
        pass

def start_wda(udid):
    if ensure_wda_running():
        return True
        
    app_path = _get_wda_bundle_path()
    if app_path:
        # Make sure it's installed to the target simulator first
        subprocess.run(["xcrun", "simctl", "install", udid, str(app_path)], check=False, capture_output=True)

    print("Starting WebDriverAgent...")
    env = os.environ.copy()
    env["SIMCTL_CHILD_USE_PORT"] = "8100"
    
    process = subprocess.Popen(
        ["xcrun", "simctl", "launch", "--terminate-running-process", udid, "com.facebook.WebDriverAgentRunner.xctrunner"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    for _ in range(15):
        time.sleep(1)
        if ensure_wda_running():
            return True
            
    process.terminate()
    return False
