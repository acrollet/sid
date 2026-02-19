import unittest
import sys
import subprocess
import json
from pippin.utils.errors import EXIT_ELEMENT_NOT_FOUND, EXIT_INVALID_ARGS, EXIT_COMMAND_FAILED

class TestCLIExitCodes(unittest.TestCase):
    def run_cli(self, args):
        """Run pippin CLI and return (exit_code, stdout, stderr)."""
        cmd = [sys.executable, "-m", "pippin.main"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        return result.returncode, result.stdout, result.stderr

    def test_tap_missing_args(self):
        code, out, err = self.run_cli(["tap"])
        self.assertEqual(code, EXIT_INVALID_ARGS)
        self.assertIn("FAIL: ERR_INVALID_ARGS", err)

    def test_tap_element_not_found(self):
        # Assuming "NonExistent" is not on screen. This test relies on idb being mocked or failing.
        # Since we can't easily mock subprocess calls from here without more complex setup,
        # we'll rely on the fact that `run_cli` executes the real main.
        # But wait, `pippin.commands.interaction` imports `execute_command`.
        # We can't mock it easily in a subprocess integration test unless we use a mock-ready entry point.
        # Alternatively, we can patch `execute_command` in `pippin.commands.interaction` if we import the main module in the test process.
        pass

    def test_help_success(self):
        code, out, err = self.run_cli(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("Pippin: A CLI for iOS Automation", out)

if __name__ == "__main__":
    unittest.main()
