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
        "Read the contents of a textfile and return its content. Only works with text compatible files. Does not support binary files.",
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

    def execute(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read a file or URL and return its contents."""
        if not file_path.strip():
            logger.error("Path cannot be empty or whitespace.")
            return "Error: Path cannot be empty."

        temp_file = None
        try:
            # First check if it's a URL before converting to Path
            if self._is_url(file_path):
                temp_file = self._download_file(file_path)
                if not temp_file:
                    raise FileReadError(f"Failed to download file from {file_path}")
                path_to_read = temp_file
            else:
                # Only convert to Path if it's a local file
                path_to_read = Path(file_path).expanduser().resolve()
                if not path_to_read.exists():
                    error_msg = f"File '{path_to_read}' does not exist."
                    logger.error(error_msg)
                    raise FileReadError(error_msg)

                if not path_to_read.is_file():
                    error_msg = f"Path '{path_to_read}' is not a file."
                    logger.error(error_msg)
                    raise FileReadError(error_msg)

            with open(path_to_read, 'r', encoding=encoding) as f:
                content = f.read()
                logger.info(f"Read file '{path_to_read}' successfully.")
                return content

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
