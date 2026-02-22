import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys
from pippin.utils.ui import find_element

class TestElementMatching(unittest.TestCase):
    def setUp(self):
        self.mock_tree = [
            {"AXIdentifier": "unique_id", "AXLabel": "Label A", "role": "Button"},
            {"AXIdentifier": "other_id", "AXLabel": "Label B", "role": "StaticText"},
            {"AXIdentifier": "", "AXLabel": "Common Label", "role": "Button"},
            {"AXIdentifier": "", "AXLabel": "Common Label Extended", "role": "Cell"},
            {"AXIdentifier": "login_btn", "AXLabel": "Login", "role": "Button"},
        ]

    @patch('pippin.utils.ui.get_ui_tree')
    def test_exact_id_match(self, mock_get_tree):
        mock_get_tree.return_value = self.mock_tree
        el = find_element("unique_id", silent=True)
        self.assertEqual(el["AXIdentifier"], "unique_id")

    @patch('pippin.utils.ui.get_ui_tree')
    def test_exact_label_match_priority(self, mock_get_tree):
        mock_get_tree.return_value = self.mock_tree
        # "Common Label" should match the exact one, not "Common Label Extended"
        el = find_element("Common Label", silent=True)
        self.assertEqual(el["AXLabel"], "Common Label")

    @patch('pippin.utils.ui.get_ui_tree')
    def test_substring_match(self, mock_get_tree):
        mock_get_tree.return_value = self.mock_tree
        # "Extended" should match "Common Label Extended"
        el = find_element("Extended", silent=True)
        self.assertEqual(el["AXLabel"], "Common Label Extended")

    @patch('pippin.utils.ui.get_ui_tree')
    def test_strict_mode_rejects_substring(self, mock_get_tree):
        mock_get_tree.return_value = self.mock_tree
        # "Extended" matches "Common Label Extended" normally, but strict should fail if not exact
        # "Common Label Extended" is the exact label, so "Extended" is a substring.
        el = find_element("Extended", strict=True, silent=True)
        self.assertIsNone(el)
        
        # Exact match should still work in strict
        el = find_element("Common Label", strict=True, silent=True)
        self.assertEqual(el["AXLabel"], "Common Label")

    @patch('pippin.utils.ui.get_ui_tree')
    def test_type_qualified_match(self, mock_get_tree):
        mock_get_tree.return_value = self.mock_tree
        # "Button:Login"
        el = find_element("Button:Login", silent=True)
        self.assertEqual(el["AXIdentifier"], "login_btn")
        
        # "Cell:Login" should not match Button
        el = find_element("Cell:Login", silent=True)
        self.assertIsNone(el)

    @patch('pippin.utils.ui.get_ui_tree')
    @patch('sys.stderr', new_callable=StringIO)
    def test_ambiguity_warning(self, mock_stderr, mock_get_tree):
        # Create tree with duplicates
        mock_get_tree.return_value = [
            {"AXLabel": "Duplicate", "role": "Button"},
            {"AXLabel": "Duplicate", "role": "Button"},
        ]
        find_element("Duplicate", silent=False)
        self.assertIn("WARN", mock_stderr.getvalue())
        self.assertIn("matched label 'Duplicate'", mock_stderr.getvalue())

    @patch('pippin.utils.ui.get_ui_tree')
    def test_is_onscreen(self, mock_get_tree):
        from pippin.utils.ui import is_onscreen
        if hasattr(is_onscreen, "screen_w"):
            delattr(is_onscreen, "screen_w")
            
        mock_get_tree.return_value = [{"role": "Window", "frame": {"width": 375, "height": 812}}]
        
        el_on = {"frame": {"x": 100, "y": 100, "width": 50, "height": 50}}
        self.assertTrue(is_onscreen(el_on))
        
        el_off_r = {"frame": {"x": 400, "y": 100, "width": 50, "height": 50}}
        self.assertFalse(is_onscreen(el_off_r))
        
        el_off_b = {"frame": {"x": 100, "y": 900, "width": 50, "height": 50}}
        self.assertFalse(is_onscreen(el_off_b))
        
        el_off_t = {"frame": {"x": 100, "y": -100, "width": 50, "height": 50}}
        self.assertFalse(is_onscreen(el_off_t))

if __name__ == "__main__":
    unittest.main()
