import unittest
import json
import sys
from unittest.mock import patch, MagicMock
from io import StringIO
import pippin.commands.context as context

class TestContextCommand(unittest.TestCase):

    @patch('pippin.commands.context.get_target_udid', return_value="UDID-1")
    @patch('pippin.commands.context.execute_command')
    def test_get_device_info(self, mock_exec, mock_udid):
        # Mock simctl output
        mock_output = json.dumps({
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-17-0": [
                    {"udid": "UDID-1", "name": "iPhone 15", "state": "Booted"},
                    {"udid": "UDID-2", "name": "iPhone 15 Pro", "state": "Shutdown"}
                ]
            }
        })
        mock_exec.return_value = mock_output
        
        info = context.get_device_info()
        self.assertEqual(info["udid"], "UDID-1")
        self.assertEqual(info["name"], "iPhone 15")
        self.assertEqual(info["runtime"], "iOS-17-0")
        self.assertEqual(info["state"], "Booted")

    def test_analyze_screen(self):
        # Mock a UI tree with a nav bar and back button
        mock_tree = [
            {
                "role": "Window",
                "nodes": [
                    {
                        "role": "NavigationBar",
                        "AXIdentifier": "Settings",
                        "nodes": [
                            {"role": "Button", "AXLabel": "Back"},
                            {"role": "Button", "AXLabel": "Edit"} # Should be ignored as breadcrumb
                        ]
                    },
                    {
                        "role": "Alert",
                        "AXLabel": "Error",
                        "nodes": [
                            {"role": "StaticText", "AXLabel": "Something went wrong"}
                        ]
                    }
                ]
            }
        ]
        
        info = context.analyze_screen(mock_tree)
        self.assertEqual(info["title"], "Settings")
        self.assertIn("Back", info["breadcrumb"])
        self.assertNotIn("Edit", info["breadcrumb"])
        self.assertEqual(info["alert"]["title"], "Error")
        self.assertEqual(info["alert"]["message"], "Something went wrong")

    @patch('pippin.commands.context.get_device_info')
    @patch('pippin.commands.context.get_app_info')
    @patch('pippin.commands.context.get_ui_tree_hierarchical')
    @patch('pippin.commands.context.screenshot_cmd')
    def test_context_cmd_structure(self, mock_screenshot, mock_get_tree, mock_get_app, mock_get_device):
        mock_get_device.return_value = {"name": "iPhone"}
        mock_get_app.return_value = {"bundle_id": "com.test", "state": "running"}
        mock_get_tree.return_value = [{"role": "Window"}]
        
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            context.context_cmd(include_logs=False, screenshot_path="shot.png", brief=False)
        finally:
            sys.stdout = sys.__stdout__
            
        output = captured_output.getvalue()
        result = json.loads(output)
        
        self.assertEqual(result["device"]["name"], "iPhone")
        self.assertEqual(result["app"]["bundle_id"], "com.test")
        self.assertEqual(result["screenshot"], "shot.png")
        self.assertTrue(mock_screenshot.called)
        self.assertIn("ui", result)

    @patch('pippin.commands.context.get_device_info')
    @patch('pippin.commands.context.get_app_info')
    @patch('pippin.commands.context.get_ui_tree_hierarchical')
    def test_context_cmd_brief(self, mock_get_tree, mock_get_app, mock_get_device):
        mock_get_device.return_value = {}
        mock_get_app.return_value = {}
        mock_get_tree.return_value = []
        
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            context.context_cmd(brief=True)
        finally:
            sys.stdout = sys.__stdout__
            
        output = captured_output.getvalue()
        result = json.loads(output)
        
        self.assertNotIn("ui", result)

    @patch('pippin.commands.context.execute_command')
    def test_get_device_info_failure(self, mock_exec):
        mock_exec.return_value = "" # Empty output
        info = context.get_device_info()
        self.assertIsNone(info)

if __name__ == "__main__":
    unittest.main()
