import sys

# Exit codes
EXIT_SUCCESS = 0
EXIT_ELEMENT_NOT_FOUND = 1
EXIT_TIMEOUT = 2
EXIT_APP_NOT_RUNNING = 3
EXIT_COMMAND_FAILED = 4
EXIT_INVALID_ARGS = 5

# Structured error prefixes (for stderr)
ERR_ELEMENT_NOT_FOUND = "ERR_ELEMENT_NOT_FOUND"
ERR_COORDINATES_NOT_FOUND = "ERR_COORDINATES_NOT_FOUND"
ERR_TIMEOUT = "ERR_TIMEOUT"
ERR_NO_TARGET_APP = "ERR_NO_TARGET_APP"
ERR_APP_CRASHED = "ERR_APP_CRASHED"
ERR_TEXT_MISMATCH = "ERR_TEXT_MISMATCH"
ERR_COMMAND_FAILED = "ERR_COMMAND_FAILED"
ERR_INVALID_ARGS = "ERR_INVALID_ARGS"

def fail(error_code: str, message: str, exit_code: int = EXIT_COMMAND_FAILED):
    """Print structured error to stderr and exit with appropriate code."""
    print(f"FAIL: {error_code}: {message}", file=sys.stderr)
    sys.exit(exit_code)
