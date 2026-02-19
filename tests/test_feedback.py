import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys
import json
from pippin.utils.capture import capture_output

class TestFeedbackLoop(unittest.TestCase):
    def test_capture_output(self):
        with capture_output() as (out, err):
            print("stdout msg")
            print("stderr msg", file=sys.stderr)
        self.assertEqual(out.getvalue().strip(), "stdout msg")
        self.assertEqual(err.getvalue().strip(), "stderr msg")

    # Testing main.py logic is hard without full integration, 
    # but we can try to verify the JSON value parsing logic if we extracted it.
    # For now, let's trust the integration test or manual verification.
    # We can at least verify that the capture context manager works as expected.

if __name__ == "__main__":
    unittest.main()
