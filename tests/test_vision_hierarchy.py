import unittest
import json
import sys
from unittest.mock import patch, MagicMock
from io import StringIO
import sid.commands.vision as vision

class TestVisionHierarchy(unittest.TestCase):

    @patch('sid.commands.vision.get_ui_tree_hierarchical')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="com.dynamic.app")
    def test_inspect_hierarchical(self, mock_file, mock_exists, mock_get_tree):
        # Mock tree structure
        mock_tree = {
            "role": "Window", "AXIdentifier": "LoginView", "frame": {"x": 0, "y": 0, "w": 375, "h": 812},
            "nodes": [
                {
                    "role": "NavigationBar",
                    "nodes": [
                         {"role": "Button", "AXIdentifier": "Back", "AXLabel": "Back", "frame": {"x": 0, "y": 20, "w": 50, "h": 50}}
                    ]
                },
                {
                    "role": "Table",
                    "nodes": [
                         {"role": "Cell", "AXLabel": "Row 1", "frame": {"x": 0, "y": 100, "w": 375, "h": 50}, "nodes": [
                              {"role": "StaticText", "AXLabel": "Row 1 Text"}
                         ]}
                    ]
                }
            ]
        }
        mock_get_tree.return_value = mock_tree
        mock_exists.return_value = True

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            vision.inspect_cmd(interactive_only=True, flat=False)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        data = json.loads(output)

        self.assertEqual(data["app"], "com.dynamic.app")
        self.assertEqual(data["screen_id"], "LoginView")

        # Check hierarchy
        # Window is "structural" and "application" role, so it might be kept or pruned depending on logic
        # logic: is_structural = role in [..., "window", "application"]
        # so Window is structural.
        # it has children (NavigationBar, Table), so it should be kept.

        self.assertEqual(len(data["elements"]), 1)
        window = data["elements"][0]
        self.assertEqual(window["type"], "Window")

        # Check children of Window
        children = window.get("children", [])
        self.assertEqual(len(children), 2)

        nav_bar = children[0]
        self.assertEqual(nav_bar["type"], "NavigationBar")
        self.assertEqual(len(nav_bar["children"]), 1)
        self.assertEqual(nav_bar["children"][0]["type"], "Button")

        table = children[1]
        self.assertEqual(table["type"], "Table")
        self.assertEqual(len(table["children"]), 1)
        cell = table["children"][0]
        self.assertEqual(cell["type"], "Cell")

    @patch('sid.commands.vision.get_ui_tree')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="com.dynamic.app")
    def test_inspect_flat(self, mock_file, mock_exists, mock_get_tree):
        # Mock flat list
        mock_data = [
            {"role": "Window", "AXIdentifier": "LoginView", "frame": {"x": 0, "y": 0, "w": 375, "h": 812}},
            {"role": "Button", "AXIdentifier": "btn1", "AXLabel": "Login", "frame": {"x": 10, "y": 20, "w": 100, "h": 50}},
        ]
        mock_get_tree.return_value = mock_data
        mock_exists.return_value = True

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            vision.inspect_cmd(interactive_only=True, flat=True)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        data = json.loads(output)

        self.assertEqual(data["app"], "com.dynamic.app")
        self.assertIn("elements", data)
        # In flat mode, Window is filtered out if interactive_only=True
        # because Window is not in valid_roles list for interactive_only in flat mode logic.
        # Check flat mode logic:
        # valid_roles = ["button", ...] -- Window is not there.
        self.assertEqual(len(data["elements"]), 1)
        self.assertEqual(data["elements"][0]["type"], "Button")

    def test_simplify_node_logic(self):
        # Test pruning
        # A Group (Unknown/Other) with no interactive children should be pruned
        node = {
            "role": "Group",
            "nodes": [
                {"role": "Image", "AXIdentifier": "icon"} # Image is interactive? yes
            ]
        }
        simplified = vision.simplify_node(node, interactive_only=True)
        self.assertIsNotNone(simplified)
        self.assertEqual(simplified["type"], "Group")
        self.assertEqual(len(simplified["children"]), 1)

        node2 = {
            "role": "Group",
            "nodes": [
                {"role": "Other", "nodes": []}
            ]
        }
        simplified2 = vision.simplify_node(node2, interactive_only=True)
        self.assertIsNone(simplified2)

if __name__ == "__main__":
    unittest.main()
