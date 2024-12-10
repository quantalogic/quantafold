import logging
import subprocess
from typing import Optional

from models.observation import Observation

logger = logging.getLogger(__name__)


def execute_shell_command(command: str) -> Observation:
    """
    Execute a shell command and return its output.

    Args:
        command: The shell command to execute

    Returns:
        Observation: An observation containing the command output or error
    """
    try:
        # Execute the command and capture output
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )

        # Return successful output
        return Observation(value=result.stdout, error=None)

    except subprocess.CalledProcessError as e:
        # Handle command execution errors
        error_msg = f"Command failed with exit code {e.returncode}. Error: {e.stderr}"
        logger.error(error_msg)
        return Observation(value=None, error=error_msg)

    except Exception as e:
        # Handle other potential errors
        error_msg = f"Error executing command: {str(e)}"
        logger.error(error_msg)
        return Observation(value=None, error=error_msg)
