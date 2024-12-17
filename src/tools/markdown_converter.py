import logging
import tempfile
import urllib.parse
from pathlib import Path
from typing import List, Optional

import requests
from markitdown import MarkItDown
from models.tool import Tool, ToolArgument
from pydantic import Field

from .file_reader import FileReadError

logger = logging.getLogger(__name__)


class MarkdownConversionError(Exception):
    """Custom exception for markdown conversion errors."""

    pass


class MarkdownConverterTool(Tool):
    name: str = Field(
        "READ_AND_CONVERT_TO_MARKDOWN_TOOL", description="A file reader that convert to markdown."
    )
    description: str = Field(
        "A file reader that converts files or URLs (PDF, DOCX, XLSX, etc.) to Markdown format.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="path",
                type="string",
                description="The path to the file or URL to convert.",
                required=True,
            )
        ]
    )

    need_validation: bool = Field(
        False, description="Indicates if the tool needs validation."
    )

    def _is_url(self, path: str) -> bool:
        """Check if the given path is a URL."""
        try:
            result = urllib.parse.urlparse(path)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def _download_file(self, url: str) -> Optional[Path]:
        """Download a file from a URL and return its temporary path."""
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                response = requests.get(url, stream=True)
                response.raise_for_status()

                # Try to get the filename from Content-Disposition header
                content_disposition = response.headers.get("content-disposition")
                if content_disposition and "filename=" in content_disposition:
                    filename = content_disposition.split("filename=")[1].strip("\"'")
                else:
                    # Use the last part of the URL as filename
                    filename = url.split("/")[-1]

                temp_path = Path(temp_file.name)
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)

                logger.info(f"Downloaded file from {url} to {temp_path}")
                return temp_path

        except Exception as e:
            logger.error(f"Error downloading file from {url}: {str(e)}")
            return None

    def execute(self, path: str) -> str:
        """Convert a file or URL to markdown format."""
        if not path.strip():
            logger.error("Path cannot be empty or whitespace.")
            return "Error: Path cannot be empty."

        temp_file = None
        try:
            if self._is_url(path):
                temp_file = self._download_file(path)
                if not temp_file:
                    raise MarkdownConversionError(
                        f"Failed to download file from {path}"
                    )
                file_path = temp_file
            else:
                file_path = Path(path)
                if not file_path.exists():
                    error_msg = f"File '{file_path}' does not exist."
                    logger.error(error_msg)
                    raise FileReadError(error_msg)

                if not file_path.is_file():
                    error_msg = f"Path '{file_path}' is not a file."
                    logger.error(error_msg)
                    raise FileReadError(error_msg)

            markitdown = MarkItDown()
            result = markitdown.convert(str(file_path))

            logger.info(
                f"Successfully converted {'URL' if temp_file else 'file'} to markdown: {path}"
            )
            return result.text_content

        except Exception as e:
            error_msg = f"Error converting {'URL' if temp_file else 'file'} '{path}' to markdown: {str(e)}"
            logger.error(error_msg)
            raise MarkdownConversionError(error_msg) from e

        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(
                        f"Failed to clean up temporary file {temp_file}: {str(e)}"
                    )
