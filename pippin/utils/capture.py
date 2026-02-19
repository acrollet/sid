import sys
from io import StringIO
import contextlib

@contextlib.contextmanager
def capture_output():
    """Captures stdout and stderr within the context."""
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield new_out, new_err
    finally:
        sys.stdout, sys.stderr = old_out, old_err
