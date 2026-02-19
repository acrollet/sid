import unittest
from unittest.mock import patch, MagicMock
from pippin.utils.device import get_target_udid, set_target_device
import pippin.utils.device

class TestDeviceTargeting(unittest.TestCase):
    def setUp(self):
        # Reset global state
        pippin.utils.device._target_udid = None
    
    @patch('pippin.utils.device.execute_command')
    def test_auto_select_single_device(self, mock_exec):
        mock_exec.return_value = '''
        {
          "devices": {
            "iOS 17.0": [
              {"udid": "A", "state": "Booted", "name": "iPhone 15"}
            ]
          }
        }
        '''
        self.assertEqual(get_target_udid(), "A")

    @patch('pippin.utils.device.execute_command')
    def test_fail_multiple_devices_no_flag(self, mock_exec):
        mock_exec.return_value = '''
        {
          "devices": {
            "iOS 17.0": [
              {"udid": "A", "state": "Booted", "name": "iPhone 15"},
              {"udid": "B", "state": "Booted", "name": "iPad Pro"}
            ]
          }
        }
        '''
        with self.assertRaises(SystemExit):
            get_target_udid()

    @patch('pippin.utils.device.execute_command')
    def test_select_specific_device_via_flag(self, mock_exec):
        # Even if multiple are booted, flag should win and skip listing if passed early,
        # but get_target_udid checks global variable.
        set_target_device("B")
        self.assertEqual(get_target_udid(), "B")
        mock_exec.assert_not_called()

if __name__ == "__main__":
    unittest.main()
