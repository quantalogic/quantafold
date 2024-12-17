import logging
import tempfile
import urllib.parse
from pathlib import Path
from typing import List, Optional

import requests
from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class FileReadError(Exception):
    """Custom exception for file reading errors."""

    pass


class FileReaderTool(Tool):
    name: str = Field("FILE_READER_TOOL", description="A file reader tool.")
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

    def _is_url(self, path: str) -> bool:
        """Check if the given path is a valid URL."""
        try:
            result = urllib.parse.urlparse(path)
            return all([result.scheme in ("http", "https"), result.netloc])
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

    def execute(self, path: str, encoding: str = "utf-8") -> str:
        """Read a file or URL and return its contents."""
        if not path.strip():
            logger.error("Path cannot be empty or whitespace.")
            return "Error: Path cannot be empty."

        temp_file = None
        try:
            if self._is_url(path):
                temp_file = self._download_file(path)
                if not temp_file:
                    raise FileReadError(f"Failed to download file from {path}")
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

            with open(file_path, encoding=encoding) as file:
                content = file.read()

            logger.info(f"Successfully read {'URL' if temp_file else 'file'}: {path}")
            return content

        except UnicodeDecodeError as e:
            error_msg = f"Failed to decode file '{path}' with encoding '{encoding}': {str(e)}"
            logger.error(error_msg)
            raise FileReadError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error reading {'URL' if temp_file else 'file'} '{path}': {str(e)}"
            logger.error(error_msg)
            raise FileReadError(error_msg) from e
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_file}: {str(e)}")
