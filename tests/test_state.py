import unittest
from unittest.mock import patch, mock_open
import os
from pippin.utils.state import get_last_bundle_id, set_last_bundle_id, STATE_FILE

class TestState(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="com.example.app")
    @patch("os.path.exists", return_value=True)
    def test_get_last_bundle_id_exists(self, mock_exists, mock_file):
        self.assertEqual(get_last_bundle_id(), "com.example.app")

    @patch("os.path.exists", return_value=False)
    def test_get_last_bundle_id_missing(self, mock_exists):
        self.assertIsNone(get_last_bundle_id())

    @patch("builtins.open", new_callable=mock_open)
    def test_set_last_bundle_id(self, mock_file):
        set_last_bundle_id("com.test.app")
        mock_file.assert_called_with(STATE_FILE, "w")
        mock_file().write.assert_called_with("com.test.app")

if __name__ == "__main__":
    unittest.main()
