import logging
import mimetypes
import tempfile
import urllib.parse
from pathlib import Path
from typing import ClassVar, List, Optional, Set, Tuple

import requests
from markitdown import MarkItDown
from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class FileReadError(Exception):
    """Custom exception for file reading errors."""

    pass


class FileReaderTool(Tool):
    # Add constants for file validation
    MAX_FILE_SIZE: ClassVar[int] = 10 * 1024 * 1024  # 10MB
    TIMEOUT: ClassVar[int] = 30  # seconds
    ALLOWED_MIME_TYPES: ClassVar[Set[str]] = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "text/x-markdown",
        "text/html",
        "text/xml",
        "application/json",
        "text/csv",
        "application/x-yaml",
        "text/yaml",
        "text/x-python",
        "text/x-java-source",
        "text/javascript",
        "application/javascript",
    }

    name: str = Field(
        "FileReaderTool",
        description="A file reader tool that supports both text and binary files, converting binary files to markdown.",
    )
    description: str = Field(
        "Read files and return contents. Supports text files directly and converts binary files (PDF, DOCX) to markdown.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="file_path",
                type="string",
                description="The path to the file to read. It can be a file path or a URL.",
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

    def _is_url(self, path: str) -> bool:
        """Check if the given path is a valid URL."""
        try:
            result = urllib.parse.urlparse(path)
            return all([result.scheme in ("http", "https"), result.netloc])
        except ValueError:
            return False

    def _extract_mime_from_headers(self, headers: dict) -> Optional[str]:
        """Extract and validate MIME type from HTTP headers."""
        content_type = headers.get("content-type", "").lower()
        if not content_type:
            return None

        # Split content type and remove parameters
        mime_type = content_type.split(";")[0].strip()

        # Special handling for text types with charset
        if mime_type.startswith("text/") or mime_type in self.ALLOWED_MIME_TYPES:
            return mime_type

        return None

    def _get_mime_type(
        self, file_path: Path, content_type: str = None
    ) -> Optional[str]:
        """Get MIME type from content-type header or file extension."""
        if content_type:
            # Clean up content type string
            mime_type = content_type.split(";")[0].strip().lower()
            if mime_type in self.ALLOWED_MIME_TYPES:
                return mime_type

        # Try to guess from file extension
        mime_type = mimetypes.guess_type(str(file_path))[0]
        if mime_type and mime_type in self.ALLOWED_MIME_TYPES:
            return mime_type

        # Check common text file extensions
        suffix = file_path.suffix.lower()
        extension_map = {
            ".md": "text/markdown",
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".json": "application/json",
            ".yaml": "application/x-yaml",
            ".yml": "application/x-yaml",
            ".xml": "text/xml",
            ".html": "text/html",
            ".htm": "text/html",
            ".csv": "text/csv",
            ".txt": "text/plain",
        }

        return extension_map.get(suffix)

    def _validate_file(self, file_path: Path, content_type: str = None) -> bool:
        """Validate file size and type. Returns True if file needs markdown conversion."""
        if file_path.stat().st_size > self.MAX_FILE_SIZE:
            raise FileReadError(
                f"File size exceeds {self.MAX_FILE_SIZE/1024/1024}MB limit"
            )

        mime_type = self._get_mime_type(file_path, content_type)
        if not mime_type:
            # If no mime type detected, try as text file
            return False

        if mime_type in self.ALLOWED_MIME_TYPES and mime_type != "text/plain":
            return True

        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise FileReadError(f"Unsupported file type: {mime_type}")

        return False

    def _download_file(self, url: str) -> Tuple[Optional[Path], Optional[str]]:
        """Download a file from a URL and return the file path and content type."""
        try:
            response = requests.get(
                url,
                stream=True,
                timeout=self.TIMEOUT,
                headers={"User-Agent": "FileReader/1.0"},
            )
            response.raise_for_status()

            content_length = int(response.headers.get("content-length", 0))
            if content_length > self.MAX_FILE_SIZE:
                raise FileReadError(
                    f"File size exceeds {self.MAX_FILE_SIZE/1024/1024}MB limit"
                )

            content_type = self._extract_mime_from_headers(response.headers)
            with tempfile.NamedTemporaryFile(
                suffix=Path(url).suffix, delete=False
            ) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                return Path(temp_file.name), content_type

        except requests.exceptions.RequestException as e:
            raise FileReadError(f"Failed to download file: {str(e)}")

    def execute(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read a file or URL and return its contents, converting to markdown if needed."""
        if not file_path.strip():
            logger.error("Path cannot be empty or whitespace.")
            return "Error: Path cannot be empty."

        temp_file = None
        content_type = None
        try:
            # Handle URL or local file
            if self._is_url(file_path):
                temp_file, content_type = self._download_file(file_path)
                if not temp_file:
                    raise FileReadError(f"Failed to download file from {file_path}")
                path_to_read = temp_file
            else:
                path_to_read = Path(file_path).expanduser().resolve()
                if not path_to_read.exists():
                    raise FileReadError(f"File '{path_to_read}' does not exist.")
                if not path_to_read.is_file():
                    raise FileReadError(f"Path '{path_to_read}' is not a file.")

            # Validate and determine if markdown conversion is needed
            needs_conversion = self._validate_file(path_to_read, content_type)

            if needs_conversion:
                # Convert binary file to markdown
                markitdown = MarkItDown()
                result = markitdown.convert(str(path_to_read))
                return result.text_content
            else:
                # Read as text file
                with open(path_to_read, "r", encoding=encoding) as f:
                    return f.read()

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error for file '{file_path}': {str(e)}")
            return f"Error: Unable to decode file '{file_path}' with encoding '{encoding}'."
        except FileReadError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return "Error: An unexpected error occurred while reading the file."
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(
                        f"Failed to clean up temporary file {temp_file}: {str(e)}"
                    )
