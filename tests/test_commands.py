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
    def test_inspect_basic(self, mock_get_tree):
        # Mock tree structure
        mock_data = [
            {"role": "Button", "AXIdentifier": "btn1", "AXLabel": "Login", "frame": {"x": 10, "y": 20, "w": 100, "h": 50}},
            {"role": "Window", "AXIdentifier": "win1", "frame": {"x": 0, "y": 0, "w": 375, "h": 812}}
        ]
        mock_get_tree.return_value = mock_data

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            vision.inspect_cmd(interactive_only=True)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
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

    @patch('sid.utils.ui.get_ui_tree')
    def test_assert_fail(self, mock_get_tree):
        mock_data = [] # Empty
        mock_get_tree.return_value = mock_data

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            with self.assertRaises(SystemExit):
                verification.assert_cmd("btn1", "exists")
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue().strip()
        self.assertTrue(output.startswith("FAIL"))

if __name__ == "__main__":
    unittest.main()
