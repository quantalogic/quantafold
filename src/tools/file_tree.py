import logging
import os
from pathlib import Path
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
                required=True,
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
        try:
            # Expand ~ to user's home directory and resolve path
            directory = os.path.expanduser(directory)
            directory = os.path.abspath(directory)

            # Validate depth parameter
            try:
                depth_int = int(depth)
                if depth_int < 0:
                    return "Error: Depth must be a non-negative integer."
            except ValueError:
                return "Error: Depth must be a valid integer."

            if not os.path.exists(directory):
                return f"Error: Path '{directory}' does not exist."

            if not os.path.isdir(directory):
                return f"Error: Path '{directory}' is not a directory."

            if not os.access(directory, os.R_OK):
                return f"Error: No read permission for '{directory}'"

            tree_view = self._build_tree_view(directory, depth_int, 0)
            logger.info("Successfully built tree view.")
            return tree_view
        except Exception as e:
            error_msg = f"Error listing files in directory '{directory}': {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _build_tree_view(
        self, directory: str, max_depth: int, current_depth: int
    ) -> str:
        """Recursively build a tree view of files and directories."""
        if max_depth != 0 and current_depth >= max_depth:
            return ""

        tree = ""
        try:
            entries = sorted(
                os.listdir(directory),
                key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x),
            )
            for entry in entries:
                try:
                    entry_path = os.path.join(directory, entry)
                    is_dir = os.path.isdir(entry_path)
                    nature = "Directory" if is_dir else "File"

                    try:
                        entry_size = os.path.getsize(entry_path) if not is_dir else "-"
                        size_str = (
                            f"{entry_size:,} bytes"
                            if isinstance(entry_size, int)
                            else "-"
                        )
                    except OSError:
                        size_str = "??? bytes"

                    tree += (
                        "  " * current_depth
                        + f"- {entry} ({nature}, Size: {size_str})\n"
                    )

                    if is_dir:
                        tree += self._build_tree_view(
                            entry_path, max_depth, current_depth + 1
                        )
                except (OSError, PermissionError) as e:
                    tree += "  " * current_depth + f"- {entry} (Error: {str(e)})\n"

            return tree
        except Exception as e:
            logger.error(f"Error accessing directory '{directory}': {str(e)}")
            raise FileListingError(f"Could not access directory: {str(e)}") from e
