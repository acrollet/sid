import unittest
from sid.utils.executor import execute_command, set_dry_run, register_mock_response, clear_mock_responses
import subprocess

class TestExecutor(unittest.TestCase):
    def setUp(self):
        set_dry_run(True)
        clear_mock_responses()

    def test_mock_response(self):
        register_mock_response(["ls", "-l"], "file1\nfile2")
        output = execute_command(["ls", "-l"])
        self.assertEqual(output, "file1\nfile2")

    def test_unregistered_mock(self):
        output = execute_command(["echo", "hello"])
        self.assertEqual(output, "")

if __name__ == '__main__':
    unittest.main()
