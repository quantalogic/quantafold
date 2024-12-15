import logging
from pathlib import Path
from typing import List

from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class FileWriteError(Exception):
    """Custom exception for file writing errors."""

    pass


class FileWriterTool(Tool):
    name: str = Field("FILE_WRITER", description="A file writer tool.")
    description: str = Field(
        "Write content to a file, creating the file if it doesn't exist.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="file_path",
                type="string",
                description="The absolute or relative path where the file should be written. If directories in the path don't exist, they will be created automatically.",
                required=True,
            ),
            ToolArgument(
                name="content",
                type="string",
                description="""
                            The text content to write to the file. Must not be empty.
                            Supports dynamic content interpolation using $$$step_name$$$ syntax.
                            Examples:
                            - Simple text: 'Hello world'
                            - With interpolation: 'Result: $$$step_1$$$'
                            - Multiple interpolations: 'First: $$$step_1$$$, Second: $$$step_2$$$'
                            """,
                required=True,
            ),
            ToolArgument(
                name="encoding",
                type="string",
                description="File encoding (e.g., 'utf-8', 'ascii', 'latin-1'). Defaults to UTF-8.",
                default="utf-8",
            ),
            ToolArgument(
                name="mode",
                type="string",
                description="File writing mode: 'w' to overwrite existing content, 'a' to append to existing content.",
                default="w",
            ),
        ]
    )

    need_validation: bool = Field(
        True, description="Indicates if the tool needs validation."
    )

    def execute(
        self, file_path: str, content: str, encoding: str = "utf-8", mode: str = "w"
    ) -> str:
        """Write content to a file."""
        if not file_path.strip():
            logger.error("File path cannot be empty or whitespace.")
            raise ValueError("Error: file_path parameter cannot be empty.")

        if mode not in ["w", "a"]:
            logger.error(f"Invalid mode: {mode}. Must be 'w' or 'a'.")
            raise ValueError(
                "Error: Invalid file mode parameter. Use 'w' for write or 'a' for append."
            )

        if not content.strip():
            logger.error("Content cannot be empty or whitespace.")
            raise ValueError("Error: content parameter cannot be empty")

        try:
            file_path = Path(file_path)

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, mode=mode, encoding=encoding) as file:
                file.write(content)

            logger.info(f"Successfully wrote to file: {file_path}")
            return f"Successfully wrote {len(content)} characters to {file_path}"

        except Exception as e:
            error_msg = f"Error writing to file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise FileWriteError(error_msg) from e
