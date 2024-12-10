import logging
import subprocess

from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class ShellCommandTool(Tool):
    name: str = Field("SHELL_COMMAND", description="The unique name of the tool.")
    description: str = Field("Execute a shell command and return its output.", description="A brief description of what the tool does.")
    arguments: list[ToolArgument] = Field(default=[
        ToolArgument(
            name="command",
            type="string",
            description="The shell command to execute."
        )
    ])
    need_validation: bool = Field(True, description="Indicates if the tool needs validation.")

    def execute(self, command: str) -> str:
        """Execute a shell command and return its output."""
        try:
            result = subprocess.run(
                command, shell=True, check=True, capture_output=True, text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed with exit code {e.returncode}. Error: {e.stderr}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            logger.error(error_msg)
            return error_msg