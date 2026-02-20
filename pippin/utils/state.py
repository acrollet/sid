import os

STATE_FILE = "/tmp/pippin_last_bundle_id"

def get_last_bundle_id() -> str | None:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return f.read().strip() or None
        except IOError:
            return None
    return None

def set_last_bundle_id(bundle_id: str):
    try:
        with open(STATE_FILE, "w") as f:
            f.write(bundle_id)
    except IOError:
        pass
