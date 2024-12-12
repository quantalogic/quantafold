import logging
from pathlib import Path
from typing import List

from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class FileReadError(Exception):
    """Custom exception for file reading errors."""

    pass


class FileReaderTool(Tool):
    name: str = Field("FILE_READER", description="A file reader tool.")
    description: str = Field(
        "Read the contents of a file and return its content.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="file_path",
                type="string",
                description="The path to the file to read.",
                required=True,
            ),
            ToolArgument(
                name="encoding",
                type="string",
                description="The encoding to use when reading the file.",
                default="utf-8",
            ),
        ]
    )

    need_validation: bool = Field(
        False, description="Indicates if the tool needs validation."
    )

    def execute(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read a file and return its contents."""
        if not file_path.strip():
            logger.error("File path cannot be empty or whitespace.")
            return "Error: File path cannot be empty."

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                error_msg = f"File '{file_path}' does not exist."
                logger.error(error_msg)
                raise FileReadError(error_msg)

            if not file_path.is_file():
                error_msg = f"Path '{file_path}' is not a file."
                logger.error(error_msg)
                raise FileReadError(error_msg)

            with open(file_path, encoding=encoding) as file:
                content = file.read()

            logger.info(f"Successfully read file: {file_path}")
            return content

        except UnicodeDecodeError as e:
            error_msg = f"Failed to decode file '{file_path}' with encoding '{encoding}': {str(e)}"
            logger.error(error_msg)
            raise FileReadError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error reading file '{file_path}': {str(e)}"
            logger.error(error_msg)
            raise FileReadError(error_msg) from e
