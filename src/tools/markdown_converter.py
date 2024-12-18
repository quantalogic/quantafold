import logging
import mimetypes
import tempfile
import urllib.parse
from pathlib import Path
from typing import ClassVar, List, Optional, Set
from urllib.parse import urlparse

import requests
from markitdown import MarkItDown
from models.tool import Tool, ToolArgument
from pydantic import Field

from .file_reader import FileReadError

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


class DownloadError(Exception):
    """Raised when file download fails."""

    pass


class MarkdownConverterTool(Tool):
    """Tool for converting various file formats to Markdown.

    Supports:
    - Local files (PDF, DOCX, XLSX)
    - Remote URLs

    Example:
        >>> converter = MarkdownConverterTool()
        >>> markdown = converter.execute("document.pdf")
    """

    # Constants with proper type annotations
    MAX_FILE_SIZE: ClassVar[int] = 10 * 1024 * 1024  # 10MB
    TIMEOUT: ClassVar[int] = 30  # seconds
    ALLOWED_MIME_TYPES: ClassVar[Set[str]] = {
        "application/pdf",
        "application/msword",
        "text/plain",
    }

    name: str = Field(
        "READ_AND_CONVERT_TO_MARKDOWN_TOOL",
        description="A file reader that converts a PDF, DOCX, XLSX file to to markdown to simplify the text reading, supporting URLs and file paths.",
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

    def _validate_file(self, file_path: Path) -> None:
        """Validate file size and type."""
        if file_path.stat().st_size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"File size exceeds {self.MAX_FILE_SIZE/1024/1024}MB limit"
            )

        mime_type = mimetypes.guess_type(str(file_path))[0]
        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise ValidationError(f"Unsupported file type: {mime_type}")

    def _download_file(self, url: str) -> Optional[Path]:
        """Download a file from a URL with security checks."""
        try:
            response = requests.get(
                url,
                stream=True,
                timeout=self.TIMEOUT,
                headers={"User-Agent": "MarkdownConverter/1.0"},
            )
            response.raise_for_status()

            content_length = int(response.headers.get("content-length", 0))
            if content_length > self.MAX_FILE_SIZE:
                raise ValidationError(
                    f"File size exceeds {self.MAX_FILE_SIZE/1024/1024}MB limit"
                )

            content_type = response.headers.get("content-type", "")
            if content_type not in self.ALLOWED_MIME_TYPES:
                raise ValidationError(f"Unsupported content type: {content_type}")

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                return Path(temp_file.name)

        except requests.exceptions.RequestException as e:
            raise DownloadError(f"Failed to download file: {str(e)}")

    def execute(self, path: str) -> str:
        """Convert a file or URL to markdown format.

        Args:
            path: File path or URL to convert

        Returns:
            Converted markdown content

        Raises:
            ValidationError: If input validation fails
            DownloadError: If URL download fails
            MarkdownConversionError: If conversion fails
        """
        if not path.strip():
            raise ValidationError("Path cannot be empty")

        temp_file = None
        try:
            file_path = Path(path).expanduser().resolve()

            if self._is_url(path):
                temp_file = self._download_file(path)
                if not temp_file:
                    raise DownloadError(f"Failed to download {path}")
                file_path = temp_file
            else:
                if not file_path.exists():
                    raise FileReadError(f"File '{file_path}' does not exist")
                if not file_path.is_file():
                    raise FileReadError(f"Path '{file_path}' is not a file")

            self._validate_file(file_path)

            with MarkItDown() as markitdown:
                result = markitdown.convert(str(file_path))
                return result.text_content

        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")
