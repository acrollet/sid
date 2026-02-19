import unittest
import sys
from io import StringIO
from unittest.mock import patch
from pippin.utils.errors import fail, EXIT_COMMAND_FAILED, ERR_COMMAND_FAILED

class TestErrors(unittest.TestCase):
    def test_fail(self):
        with patch('sys.stderr', new=StringIO()) as fake_err:
            with self.assertRaises(SystemExit) as cm:
                fail(ERR_COMMAND_FAILED, "Something went wrong", EXIT_COMMAND_FAILED)
            
            self.assertEqual(cm.exception.code, EXIT_COMMAND_FAILED)
            self.assertIn("FAIL: ERR_COMMAND_FAILED: Something went wrong", fake_err.getvalue())

if __name__ == "__main__":
    unittest.main()
