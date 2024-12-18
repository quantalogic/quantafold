import pytest
from pathlib import Path
import tempfile
import requests
from unittest.mock import Mock, patch
import vcr

# Update imports to use absolute imports from src
from src.tools.markdown_converter import (
    MarkdownConverterTool,
    ValidationError,
    DownloadError,
)


@pytest.fixture
def converter():
    return MarkdownConverterTool()


@pytest.fixture
def sample_pdf():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 dummy content")
        return Path(f.name)


def test_is_url(converter):
    assert converter._is_url("https://example.com/doc.pdf") == True
    assert converter._is_url("http://test.org/file.pdf") == True
    assert converter._is_url("/local/path/file.pdf") == False
    assert converter._is_url("relative/path/file.pdf") == False


def test_validate_file(converter, sample_pdf):
    # Should pass without raising exception
    converter._validate_file(sample_pdf)

    # Test file size validation
    with patch.object(Path, "stat") as mock_stat:
        mock_stat.return_value.st_size = MarkdownConverterTool.MAX_FILE_SIZE + 1
        with pytest.raises(ValidationError, match="File size exceeds"):
            converter._validate_file(sample_pdf)


def test_download_file(converter):
    mock_response = Mock()
    mock_response.headers = {
        "content-length": "1000",
        "content-type": "application/pdf",
    }
    mock_response.iter_content.return_value = [b"content"]

    with patch("requests.get", return_value=mock_response) as mock_get:
        result = converter._download_file("https://example.com/doc.pdf")
        assert result.exists()
        result.unlink()  # Cleanup

    # Test download error
    with patch("requests.get", side_effect=requests.exceptions.RequestException):
        with pytest.raises(DownloadError):
            converter._download_file("https://example.com/doc.pdf")


def test_execute_validation(converter):
    with pytest.raises(ValidationError):
        converter.execute("")

    with pytest.raises(ValidationError):
        converter.execute("   ")


@patch("src.tools.markdown_converter.MarkItDown")
def test_execute_conversion(mock_markitdown, converter, sample_pdf):
    # Setup mock without context manager
    mock_instance = Mock()
    mock_instance.convert.return_value.text_content = "# Converted Content"
    mock_markitdown.return_value = mock_instance

    result = converter.execute(str(sample_pdf))
    assert result == "# Converted Content"

    # Verify mock was called with resolved path
    resolved_path = str(Path(str(sample_pdf)).resolve())
    mock_instance.convert.assert_called_once_with(resolved_path)

    # Cleanup
    sample_pdf.unlink()


@vcr.use_cassette("tests/fixtures/vcr_cassettes/arxiv_pdf.yaml")
def test_arxiv_pdf_conversion(converter):
    """Test converting an arXiv PDF to markdown."""
    url = "https://arxiv.org/pdf/2412.10117.pdf"

    # Setup mock for MarkItDown
    with patch("src.tools.markdown_converter.MarkItDown") as mock_markitdown:
        mock_instance = Mock()
        mock_instance.convert.return_value.text_content = "# Title\nTest content"
        mock_markitdown.return_value = mock_instance

        # Execute conversion
        result = converter.execute(url)

        # Verify results
        assert isinstance(result, str)
        assert result.startswith("# Title")
        assert "Test content" in result

        # Verify MarkItDown was called with a valid file path
        args = mock_instance.convert.call_args[0]
        assert len(args) == 1
        assert Path(args[0]).suffix == ".pdf"
