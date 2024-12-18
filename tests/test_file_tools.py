import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from src.tools.file_reader import FileReaderTool, FileReadError
from src.tools.markdown_converter import MarkdownConverterTool, ValidationError, DownloadError

@pytest.fixture
def temp_text_file():
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'Test content')
        yield Path(f.name)
    os.unlink(f.name)

@pytest.fixture
def temp_pdf_file():
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(b'%PDF-1.4\nTest PDF content')
        yield Path(f.name)
    os.unlink(f.name)

@pytest.fixture
def file_reader():
    return FileReaderTool()

@pytest.fixture
def markdown_converter():
    return MarkdownConverterTool()

class TestFileTools:
    def test_is_url(self, file_reader, markdown_converter):
        """Test URL validation for both tools"""
        valid_urls = [
            'http://example.com/file.pdf',
            'https://test.org/doc.txt'
        ]
        invalid_urls = [
            '',
            'not_a_url',
            'file:///local/path',
            '/absolute/path'
        ]
        
        for url in valid_urls:
            assert file_reader._is_url(url) is True
            assert markdown_converter._is_url(url) is True
            
        for url in invalid_urls:
            assert file_reader._is_url(url) is False
            assert markdown_converter._is_url(url) is False

    def test_get_mime_type(self, file_reader, markdown_converter, temp_text_file, temp_pdf_file):
        """Test MIME type detection"""
        # Test text file
        assert file_reader._get_mime_type(temp_text_file) == 'text/plain'
        assert markdown_converter._get_mime_type(temp_text_file) == 'text/plain'
        
        # Test PDF file
        assert file_reader._get_mime_type(temp_pdf_file) == 'application/pdf'
        assert markdown_converter._get_mime_type(temp_pdf_file) == 'application/pdf'
        
        # Test with content type override
        assert file_reader._get_mime_type(temp_text_file, 'application/pdf') == 'application/pdf'
        assert markdown_converter._get_mime_type(temp_text_file, 'application/pdf') == 'application/pdf'

    @patch('requests.get')
    def test_download_file(self, mock_get, file_reader, markdown_converter):
        """Test file download functionality"""
        # Mock successful response
        mock_response = Mock()
        mock_response.headers = {
            'content-length': '100',
            'content-type': 'application/pdf'
        }
        mock_response.iter_content.return_value = [b'Test content']
        mock_get.return_value = mock_response

        # Test successful download
        result = file_reader._download_file('https://example.com/test.pdf')
        assert result.exists()
        result.unlink()  # Cleanup

        # Test download with size limit exceeded
        mock_response.headers['content-length'] = str(FileReaderTool.MAX_FILE_SIZE + 1)
        with pytest.raises(FileReadError):
            file_reader._download_file('https://example.com/large.pdf')

        # Test download failure
        mock_get.side_effect = requests.exceptions.RequestException()
        with pytest.raises(FileReadError):
            file_reader._download_file('https://example.com/error.pdf')

    @patch('markitdown.MarkItDown')
    def test_execute_with_binary_file(self, mock_markitdown, file_reader, markdown_converter, temp_pdf_file):
        """Test execution with binary file conversion"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.convert.return_value.text_content = '# Converted Content'
        mock_markitdown.return_value = mock_instance

        # Test FileReaderTool
        result = file_reader.execute(str(temp_pdf_file))
        assert result == '# Converted Content'
        mock_instance.convert.assert_called_once_with(str(temp_pdf_file))

        # Reset mock and test MarkdownConverterTool
        mock_instance.convert.reset_mock()
        result = markdown_converter.execute(str(temp_pdf_file))
        assert result == '# Converted Content'
        mock_instance.convert.assert_called_once_with(str(temp_pdf_file))

    def test_execute_with_text_file(self, file_reader, markdown_converter, temp_text_file):
        """Test execution with text file"""
        # Test FileReaderTool
        result = file_reader.execute(str(temp_text_file))
        assert result == 'Test content'

        # Test MarkdownConverterTool
        with pytest.raises(ValidationError):
            markdown_converter.execute(str(temp_text_file))

    def test_error_handling(self, file_reader, markdown_converter):
        """Test error handling for both tools"""
        # Test empty path
        assert "Error: Path cannot be empty" in file_reader.execute("")
        with pytest.raises(ValidationError):
            markdown_converter.execute("")

        # Test non-existent file
        non_existent = "non_existent_file.pdf"
        assert "Error: File" in file_reader.execute(non_existent)
        with pytest.raises(FileReadError):
            markdown_converter.execute(non_existent)

        # Test invalid URL
        invalid_url = "https://invalid.url/test.pdf"
        assert "Error: Failed to download" in file_reader.execute(invalid_url)
        with pytest.raises(DownloadError):
            markdown_converter.execute(invalid_url)

if __name__ == '__main__':
    pytest.main([__file__])
