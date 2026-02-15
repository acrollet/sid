import subprocess
import shlex
import sys

_DRY_RUN = False
_MOCK_RESPONSES = {} # cmd_str -> output

def set_dry_run(enabled: bool):
    global _DRY_RUN
    _DRY_RUN = enabled

def clear_mock_responses():
    global _MOCK_RESPONSES
    _MOCK_RESPONSES = {}

def register_mock_response(cmd: list[str], output: str):
    """Registers a mock response for a specific command."""
    cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
    _MOCK_RESPONSES[cmd_str] = output

def execute_command(command: list[str], check: bool = True, capture_output: bool = True) -> str:
    """
    Executes a shell command.

    Args:
        command: List of command arguments.
        check: If True, raise CalledProcessError on non-zero exit code.
        capture_output: If True, return stdout.

    Returns:
        The standard output of the command if capture_output is True.
    """
    cmd_str = " ".join(shlex.quote(arg) for arg in command)

    if _DRY_RUN:
        # print(f"[DRY-RUN] Executing: {cmd_str}", file=sys.stderr)
        if cmd_str in _MOCK_RESPONSES:
            return _MOCK_RESPONSES[cmd_str]
        return ""

    try:
        result = subprocess.run(
            command,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result.stdout.strip() if result.stdout else ""
    except subprocess.CalledProcessError as e:
        # Include stderr in the error message for better debugging if available
        if capture_output:
            raise subprocess.CalledProcessError(e.returncode, e.cmd, output=e.stdout, stderr=e.stderr)
        raise e
