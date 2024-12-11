import logging
import os
from typing import List

from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class FileListingError(Exception):
    """Custom exception for file listing errors."""

    pass


class FileTreeTool(Tool):
    name: str = Field(
        "FILE_TREE_TOOL",
        description="A tool to list files in a directory in a tree view.",
    )
    description: str = Field(
        "List all files in a directory in a tree view with information about the nature of the file (file/directory) and size.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="directory",
                type="string",
                description="The directory path to list files from.",
            ),
            ToolArgument(
                name="depth",
                type="int",
                description="The depth of the tree view (default 0 for all levels).",
                default="1",
            ),
        ]
    )

    need_validation: bool = Field(
        True, description="Indicates if the tool needs validation."
    )

    def execute(self, directory: str, depth: str = "0") -> str:
        """List files in a directory in a tree view format."""
        if not os.path.isdir(directory):
            logger.error(f"The path '{directory}' is not a valid directory.")
            return "Error: The specified path is not a valid directory."

        try:
            tree_view = self._build_tree_view(directory, int(depth), 0)
            logger.info("Successfully built tree view.")
            return tree_view
        except Exception as e:
            error_msg = (
                f"Unexpected error listing files in directory '{directory}': {str(e)}"
            )
            logger.error(error_msg)
            raise FileListingError(error_msg) from e

    def _build_tree_view(
        self, directory: str, max_depth: int, current_depth: int
    ) -> str:
        """Recursively build a tree view of files and directories."""
        if max_depth != 0 and current_depth >= max_depth:
            return ""

        tree = ""
        try:
            for entry in os.listdir(directory):
                entry_path = os.path.join(directory, entry)
                entry_size = (
                    os.path.getsize(entry_path) if os.path.isfile(entry_path) else "-"
                )
                nature = "Directory" if os.path.isdir(entry_path) else "File"

                tree += (
                    "  " * current_depth + f"- {entry} ({nature}, Size: {entry_size})\n"
                )

                if os.path.isdir(entry_path):
                    tree += self._build_tree_view(
                        entry_path, max_depth, current_depth + 1
                    )

            return tree
        except Exception as e:
            logger.error(
                f"Error accessing entries in directory '{directory}': {str(e)}"
            )
            raise FileListingError(f"Could not list files in directory: {str(e)}") from e
