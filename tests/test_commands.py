import unittest
import json
import sys
from unittest.mock import patch, MagicMock
from io import StringIO

# We need to import the modules to patch them
import sid.commands.vision as vision
import sid.commands.interaction as interaction
import sid.commands.system as system
import sid.commands.verification as verification

class TestCommands(unittest.TestCase):

    @patch('sid.commands.vision.get_ui_tree')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="com.dynamic.app")
    def test_inspect_basic(self, mock_file, mock_exists, mock_get_tree):
        # Mock tree structure
        mock_data = [
            {"role": "Window", "AXIdentifier": "LoginView", "frame": {"x": 0, "y": 0, "w": 375, "h": 812}},
            {"role": "Button", "AXIdentifier": "btn1", "AXLabel": "Login", "frame": {"x": 10, "y": 20, "w": 100, "h": 50}},
        ]
        mock_get_tree.return_value = mock_data
        mock_exists.return_value = True

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            vision.inspect_cmd(interactive_only=True)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn('"app": "com.dynamic.app"', output)
        self.assertIn('"screen_id": "LoginView"', output)
        self.assertIn('"id": "btn1"', output)
        self.assertIn('"type": "Button"', output)
        self.assertNotIn('"type": "Window"', output) # Interactive only filters window

    @patch('sid.utils.ui.get_ui_tree') # Patch where find_element looks it up
    @patch('sid.commands.interaction.execute_command')
    def test_tap_with_query(self, mock_exec, mock_get_tree):
        # Mock tree
        mock_data = [
            {"role": "Button", "AXIdentifier": "btn1", "AXLabel": "Login", "frame": {"x": 10, "y": 20, "w": 100, "h": 50}}
        ]
        mock_get_tree.return_value = mock_data

        interaction.tap_cmd(query="btn1")

        # Expect tap call with center: 10+50=60, 20+25=45
        mock_exec.assert_any_call(["idb", "ui", "tap", "60.0", "45.0"])

    @patch('sid.commands.system.execute_command')
    def test_launch(self, mock_exec):
        system.launch_cmd("com.test.app", clean=True, args="-flag val", locale="en_US")

        # Check terminate call
        mock_exec.assert_any_call(["xcrun", "simctl", "terminate", "booted", "com.test.app"], check=False)
        # Check launch call
        # args="-flag val" -> ["-flag", "val"]
        expected_launch = ["xcrun", "simctl", "launch", "booted", "com.test.app", "-AppleLanguages", "(en_US)", "-AppleLocale", "en_US", "-flag", "val"]
        mock_exec.assert_any_call(expected_launch)

    @patch('sid.commands.verification.execute_command')
    @patch('sid.utils.ui.get_ui_tree')
    def test_assert_exists(self, mock_get_tree, mock_exec):
        mock_data = [
            {"role": "Button", "AXIdentifier": "btn1", "AXLabel": "Login"}
        ]
        mock_get_tree.return_value = mock_data

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            verification.assert_cmd("btn1", "exists")
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue().strip()
        self.assertEqual(output, "PASS")

    @patch('sid.commands.interaction.get_ui_tree')
    def test_scroll_dynamic_dimensions(self, mock_get_tree):
        # Mock a large window (e.g. iPad)
        mock_data = [
            {"role": "Window", "frame": {"x": 0, "y": 0, "w": 1024, "h": 1366}}
        ]
        mock_get_tree.return_value = mock_data

        with patch('sid.commands.interaction.execute_command') as mock_exec:
            interaction.scroll_cmd("down")
            
            # Get the actual call arguments
            self.assertTrue(mock_exec.called)
            args, _ = mock_exec.call_args
            cmd = args[0]
            self.assertEqual(cmd[0:3], ["idb", "ui", "swipe"])
            
            # Values for 1024x1366: 
            # cx=512.0, cy=683.0, swipe_len=546.4
            # start_y=683.0 + 273.2 = 956.2
            # end_y=683.0 - 273.2 = 409.8
            self.assertAlmostEqual(float(cmd[3]), 512.0)
            self.assertAlmostEqual(float(cmd[4]), 956.2)
            self.assertAlmostEqual(float(cmd[5]), 512.0)
            self.assertAlmostEqual(float(cmd[6]), 409.8)

    @patch('sid.utils.ui.get_ui_tree')
    def test_tap_error_code(self, mock_get_tree):
        mock_get_tree.return_value = [] # No elements
        
        captured_output = StringIO()
        sys.stderr = captured_output
        try:
            interaction.tap_cmd(query="missing_btn")
        finally:
            sys.stderr = sys.__stderr__

        output = captured_output.getvalue()
        self.assertIn("ERR_ELEMENT_NOT_FOUND", output)

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.path.getmtime')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="Crash content")
    def test_logs_crash_report(self, mock_file, mock_mtime, mock_listdir, mock_exists):
        # Mock STATE_FILE exists and contains bundle_id
        # We need to handle multiple open calls
        mock_exists.side_effect = lambda p: p == "/tmp/sid_last_bundle_id" or p == "/Users/acrollet/Library/Logs/DiagnosticReports"
        
        # First call to open is for STATE_FILE
        # Second call is for the crash report
        mock_file.side_effect = [
            unittest.mock.mock_open(read_data="com.test.app").return_value,
            unittest.mock.mock_open(read_data="Header\nStack trace line 1").return_value
        ]
        
        mock_listdir.return_value = ["app-2026-02-16.ips", "other-app.ips"]
        mock_mtime.return_value = 123456789

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            verification.logs_cmd(crash_report=True)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("CRASH_REPORT_FOUND", output)
        self.assertIn("Stack trace line 1", output)

    @patch('sid.commands.doctor.execute_command')
    @patch('shutil.which')
    @patch('builtins.input', return_value='n')
    def test_doctor_fail_no_install(self, mock_input, mock_which, mock_exec):
        # idb not found, xcrun found
        mock_which.side_effect = lambda x: "/usr/bin/xcrun" if x == "xcrun" else None
        
        captured_stdout = StringIO()
        sys.stdout = captured_stdout
        try:
            with self.assertRaises(SystemExit):
                from sid.commands.doctor import doctor_cmd
                doctor_cmd()
        finally:
            sys.stdout = sys.__stdout__

        output = captured_stdout.getvalue()
        # The prompt itself won't be in stdout because input() usually prints to stderr/terminal in some envs
        # but in unittest it often doesn't capture the prompt string if mocked.
        # Actually, let's just check if it correctly reported NOT FOUND.
        self.assertIn("❌ idb NOT FOUND", output)
        self.assertIn("⚠️  Some dependencies are missing or misconfigured.", output)

    @patch('sid.commands.doctor.execute_command')
    @patch('shutil.which')
    @patch('builtins.input', return_value='y')
    @patch('sid.commands.doctor._install_idb', return_value=True)
    def test_doctor_install_success(self, mock_install, mock_input, mock_which, mock_exec):
        # Simulate idb missing initially, then found after install
        mock_which.side_effect = ["/usr/bin/xcrun", None, "/path/to/idb"] # xcrun checked first? No, idb then xcrun
        # Correct sequence:
        # 1. shutil.which("idb") -> None
        # 2. (after install) shutil.which("idb") -> /path/to/idb
        # 3. shutil.which("xcrun") -> /usr/bin/xcrun
        mock_which.side_effect = [None, "/path/to/idb", "/usr/bin/xcrun"]
        mock_exec.return_value = "idb version 1.0"

        captured_stdout = StringIO()
        sys.stdout = captured_stdout
        try:
            from sid.commands.doctor import doctor_cmd
            doctor_cmd()
        except SystemExit:
            pass 
        finally:
            sys.stdout = sys.__stdout__

        output = captured_stdout.getvalue()
        self.assertTrue(mock_install.called)
        self.assertIn("✅ idb found at: /path/to/idb", output)

    @patch('sid.utils.ui.get_ui_tree')
    def test_wait_success(self, mock_get_tree):
        # Element found on second try
        mock_data = [
            {"role": "Button", "AXIdentifier": "btn1", "AXLabel": "Login"}
        ]
        mock_get_tree.side_effect = [[], mock_data]
        
        captured_output = StringIO()
        sys.stdout = captured_output
        with patch('time.sleep'): # Don't actually sleep
            try:
                verification.wait_cmd("btn1", timeout=5.0)
            finally:
                sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("PASS: Element 'btn1' is visible.", output)

    @patch('sid.utils.ui.get_ui_tree')
    @patch('sid.commands.interaction.execute_command')
    def test_tap_partial_label(self, mock_exec, mock_get_tree):
        # Mock tree with a long label
        mock_data = [
            {"role": "Button", "AXIdentifier": "id123", "AXLabel": "Welcome to the App", "frame": {"x": 0, "y": 0, "w": 100, "h": 100}}
        ]
        mock_get_tree.return_value = mock_data

        # Should match "Welcome"
        interaction.tap_cmd(query="Welcome")
        mock_exec.assert_any_call(["idb", "ui", "tap", "50.0", "50.0"])

    @patch('sid.commands.system.execute_command')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="com.test.app")
    def test_stop(self, mock_file, mock_exists, mock_exec):
        system.stop_cmd()
        # Verify terminate call
        mock_exec.assert_any_call(["xcrun", "simctl", "terminate", "booted", "com.test.app"])

    @patch('sid.commands.system.execute_command')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="com.test.app")
    def test_relaunch(self, mock_file, mock_exists, mock_exec):
        system.relaunch_cmd(clean=True)
        # Verify stop (terminate)
        mock_exec.assert_any_call(["xcrun", "simctl", "terminate", "booted", "com.test.app"])
        # Verify launch
        expected_launch = ["xcrun", "simctl", "launch", "booted", "com.test.app"]
        mock_exec.assert_any_call(expected_launch)

if __name__ == "__main__":
    unittest.main()
