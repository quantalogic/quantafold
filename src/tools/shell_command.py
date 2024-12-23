import logging
import subprocess
from typing import List

from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class CommandExecutionError(Exception):
    """Custom exception for command execution errors."""

    pass


class ShellCommandTool(Tool):
    name: str = Field("ShellCommandTool", description="A shell command tool.")
    description: str = Field(
        "Execute a shell command and return its output.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="command",
                type="string",
                description="The shell command to execute.",
                required=True,
            ),
            ToolArgument(
                name="timeout",
                type="int",
                description="Timeout for command execution in seconds.",
                default="30",
            ),
        ]
    )

    need_validation: bool = Field(
        True, description="Indicates if the tool needs validation."
    )

    def execute(self, command: str, timeout: str = "60") -> str:
        """Execute a shell command and return its output."""
        if not command.strip():
            logger.error("Command cannot be empty or whitespace.")
            return "Error: Command cannot be empty."

        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                timeout=int(timeout),
            )
            logger.info(f"Executed command successfully: {command}")

            content: list[str] = []

            content.append("Executed command successfully: {command}.")
            content.append("Output:")
            content.append(result.stdout.strip())
            return content

        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed with exit code {e.returncode}. Error output: {e.stderr.strip()}"
            logger.error(error_msg)
            raise CommandExecutionError(error_msg) from e
        except subprocess.TimeoutExpired as e:
            error_msg = f"Command '{command}' timed out after {timeout} seconds."
            logger.error(error_msg)
            raise CommandExecutionError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error executing command '{command}': {str(e)}"
            logger.error(error_msg)
            raise CommandExecutionError(error_msg) from e
