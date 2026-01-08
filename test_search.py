"""
Comprehensive test suite for the documentation search module.

Tests cover:
- Happy paths: successful download, extraction, indexing, and searching
- Unhappy paths: invalid URLs, network errors, invalid files, empty data
"""

import os
import zipfile
import tempfile
from unittest.mock import patch, Mock, MagicMock

import pytest
import requests

from search import (
    download_zip,
    extract_md_files,
    build_index,
    search,
    get_cached_index,
    _index_cache,
    SearchError,
    DownloadError,
    IndexingError,
    ExtractionError,
)


class TestDownloadZip:
    """Tests for the download_zip function."""
    
    # --- Happy Path Tests ---
    
    @patch('search.requests.get')
    def test_download_zip_success(self, mock_get, tmp_path):
        """Test successful zip file download."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content = Mock(return_value=[b'PK\x03\x04test_content'])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        dest_dir = str(tmp_path)
        result = download_zip("https://example.com/test.zip", dest_dir)
        
        assert result == os.path.join(dest_dir, "test.zip")
        assert os.path.exists(result)
        mock_get.assert_called_once()
    
    def test_download_zip_skip_existing(self, tmp_path):
        """Test that download is skipped if file already exists."""
        # Create a dummy file
        existing_file = tmp_path / "test.zip"
        existing_file.write_bytes(b"existing content")
        
        result = download_zip("https://example.com/test.zip", str(tmp_path))
        
        assert result == str(existing_file)
        # File should still have original content
        assert existing_file.read_bytes() == b"existing content"
    
    @patch('search.requests.get')
    def test_download_zip_creates_dest_dir(self, mock_get, tmp_path):
        """Test that destination directory is created if it doesn't exist."""
        mock_response = Mock()
        mock_response.iter_content = Mock(return_value=[b'content'])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        dest_dir = str(tmp_path / "new_dir" / "subdir")
        result = download_zip("https://example.com/test.zip", dest_dir)
        
        assert os.path.exists(dest_dir)
    
    # --- Unhappy Path Tests ---
    
    def test_download_zip_invalid_url_empty(self):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            download_zip("")
    
    def test_download_zip_invalid_url_none(self):
        """Test that None URL raises ValueError."""
        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            download_zip(None)
    
    def test_download_zip_invalid_url_format(self):
        """Test that invalid URL format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL"):
            download_zip("not-a-valid-url")
    
    def test_download_zip_invalid_url_no_scheme(self):
        """Test that URL without scheme raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL"):
            download_zip("example.com/test.zip")
    
    @patch('search.requests.get')
    def test_download_zip_timeout(self, mock_get):
        """Test that timeout raises DownloadError."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        with pytest.raises(DownloadError, match="timed out"):
            download_zip("https://example.com/test.zip")
    
    @patch('search.requests.get')
    def test_download_zip_connection_error(self, mock_get):
        """Test that connection error raises DownloadError."""
        mock_get.side_effect = requests.exceptions.ConnectionError("No connection")
        
        with pytest.raises(DownloadError, match="Connection error"):
            download_zip("https://example.com/test.zip")
    
    @patch('search.requests.get')
    def test_download_zip_http_error(self, mock_get):
        """Test that HTTP error raises DownloadError."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        with pytest.raises(DownloadError, match="HTTP error"):
            download_zip("https://example.com/test.zip")


class TestExtractMdFiles:
    """Tests for the extract_md_files function."""
    
    # --- Happy Path Tests ---
    
    def test_extract_md_files_success(self, tmp_path):
        """Test successful extraction of markdown files."""
        zip_path = tmp_path / "test.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("repo-main/docs/guide.md", "# Guide\nContent")
            zf.writestr("repo-main/docs/intro.mdx", "# Intro\nMDX content")
            zf.writestr("repo-main/src/main.py", "print('hello')")  # Should be skipped
        
        result = extract_md_files(str(zip_path))
        
        assert len(result) == 2
        filenames = [doc['filename'] for doc in result]
        assert "docs/guide.md" in filenames
        assert "docs/intro.mdx" in filenames
    
    def test_extract_md_files_removes_prefix(self, tmp_path):
        """Test that the first path component is removed."""
        zip_path = tmp_path / "test.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("fastmcp-main/docs/getting-started/welcome.mdx", "content")
        
        result = extract_md_files(str(zip_path))
        
        assert len(result) == 1
        assert result[0]['filename'] == "docs/getting-started/welcome.mdx"
    
    def test_extract_md_files_content_preserved(self, tmp_path):
        """Test that file content is correctly preserved."""
        zip_path = tmp_path / "test.zip"
        expected_content = "# Hello World\n\nThis is a test."
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("repo/README.md", expected_content)
        
        result = extract_md_files(str(zip_path))
        
        assert result[0]['content'] == expected_content
    
    def test_extract_md_files_empty_zip_no_md(self, tmp_path):
        """Test extraction from zip with no markdown files returns empty list."""
        zip_path = tmp_path / "test.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("repo/main.py", "print('hello')")
            zf.writestr("repo/data.json", '{"key": "value"}')
        
        result = extract_md_files(str(zip_path))
        
        assert result == []
    
    # --- Unhappy Path Tests ---
    
    def test_extract_md_files_invalid_path_empty(self):
        """Test that empty path raises ValueError."""
        with pytest.raises(ValueError, match="Zip path must be a non-empty string"):
            extract_md_files("")
    
    def test_extract_md_files_invalid_path_none(self):
        """Test that None path raises ValueError."""
        with pytest.raises(ValueError, match="Zip path must be a non-empty string"):
            extract_md_files(None)
    
    def test_extract_md_files_file_not_found(self):
        """Test that non-existent file raises ExtractionError."""
        with pytest.raises(ExtractionError, match="Zip file not found"):
            extract_md_files("/path/to/nonexistent.zip")
    
    def test_extract_md_files_invalid_zip(self, tmp_path):
        """Test that invalid zip file raises ExtractionError."""
        invalid_zip = tmp_path / "invalid.zip"
        invalid_zip.write_text("This is not a zip file")
        
        with pytest.raises(ExtractionError, match="Invalid or corrupted"):
            extract_md_files(str(invalid_zip))


class TestBuildIndex:
    """Tests for the build_index function."""
    
    # --- Happy Path Tests ---
    
    def test_build_index_success(self):
        """Test successful index creation."""
        documents = [
            {"filename": "doc1.md", "content": "Hello world"},
            {"filename": "doc2.md", "content": "Python programming"}
        ]
        
        index = build_index(documents)
        
        assert index is not None
    
    def test_build_index_single_document(self):
        """Test index creation with single document."""
        documents = [{"filename": "solo.md", "content": "Single document content"}]
        
        index = build_index(documents)
        
        assert index is not None
    
    # --- Unhappy Path Tests ---
    
    def test_build_index_none_documents(self):
        """Test that None documents raises ValueError."""
        with pytest.raises(ValueError, match="Documents cannot be None"):
            build_index(None)
    
    def test_build_index_not_list(self):
        """Test that non-list documents raises ValueError."""
        with pytest.raises(ValueError, match="Documents must be a list"):
            build_index({"filename": "test.md", "content": "content"})
    
    def test_build_index_empty_list(self):
        """Test that empty document list raises IndexingError."""
        with pytest.raises(IndexingError, match="Cannot build index from empty"):
            build_index([])


class TestSearch:
    """Tests for the search function."""
    
    @pytest.fixture
    def sample_index(self):
        """Create a sample index for testing."""
        documents = [
            {"filename": "demo.md", "content": "This is a demo document"},
            {"filename": "guide.md", "content": "A comprehensive guide"},
            {"filename": "tutorial.md", "content": "Step by step tutorial with demo examples"},
            {"filename": "api.md", "content": "API reference documentation"},
            {"filename": "faq.md", "content": "Frequently asked questions"}
        ]
        return build_index(documents)
    
    # --- Happy Path Tests ---
    
    def test_search_returns_results(self, sample_index):
        """Test that search returns matching documents."""
        results = search(sample_index, "demo")
        
        assert len(results) > 0
        filenames = [r['filename'] for r in results]
        assert "demo.md" in filenames or "tutorial.md" in filenames
    
    def test_search_respects_num_results(self, sample_index):
        """Test that search respects num_results parameter."""
        results = search(sample_index, "document", num_results=2)
        
        assert len(results) <= 2
    
    def test_search_returns_max_5_by_default(self, sample_index):
        """Test that search returns max 5 results by default."""
        results = search(sample_index, "the")
        
        assert len(results) <= 5
    
    # --- Unhappy Path Tests ---
    
    def test_search_none_index(self):
        """Test that None index raises ValueError."""
        with pytest.raises(ValueError, match="Index cannot be None"):
            search(None, "query")
    
    def test_search_invalid_query_type(self, sample_index):
        """Test that non-string query raises ValueError."""
        with pytest.raises(ValueError, match="Query must be a string"):
            search(sample_index, 123)
    
    def test_search_empty_query(self, sample_index):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            search(sample_index, "")
    
    def test_search_whitespace_query(self, sample_index):
        """Test that whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            search(sample_index, "   ")
    
    def test_search_invalid_num_results_zero(self, sample_index):
        """Test that zero num_results raises ValueError."""
        with pytest.raises(ValueError, match="num_results must be a positive"):
            search(sample_index, "test", num_results=0)
    
    def test_search_invalid_num_results_negative(self, sample_index):
        """Test that negative num_results raises ValueError."""
        with pytest.raises(ValueError, match="num_results must be a positive"):
            search(sample_index, "test", num_results=-1)
    
    def test_search_invalid_num_results_string(self, sample_index):
        """Test that string num_results raises ValueError."""
        with pytest.raises(ValueError, match="num_results must be a positive"):
            search(sample_index, "test", num_results="5")


class TestGetCachedIndex:
    """Tests for the get_cached_index function."""
    
    def setup_method(self):
        """Clear the cache before each test."""
        _index_cache.clear()
    
    def teardown_method(self):
        """Clear the cache after each test."""
        _index_cache.clear()
    
    # --- Happy Path Tests ---
    
    @patch('search.download_zip')
    @patch('search.extract_md_files')
    @patch('search.build_index')
    def test_get_cached_index_success(self, mock_build, mock_extract, mock_download):
        """Test successful index creation and caching."""
        mock_download.return_value = "/path/to/file.zip"
        mock_extract.return_value = [{"filename": "test.md", "content": "content"}]
        mock_index = MagicMock()
        mock_build.return_value = mock_index
        
        result = get_cached_index("https://example.com/test.zip")
        
        assert result == mock_index
        mock_download.assert_called_once_with("https://example.com/test.zip", ".")
        mock_extract.assert_called_once_with("/path/to/file.zip")
        mock_build.assert_called_once()
    
    @patch('search.download_zip')
    @patch('search.extract_md_files')
    @patch('search.build_index')
    def test_get_cached_index_caches_result(self, mock_build, mock_extract, mock_download):
        """Test that subsequent calls return cached index without re-downloading."""
        mock_download.return_value = "/path/to/file.zip"
        mock_extract.return_value = [{"filename": "test.md", "content": "content"}]
        mock_index = MagicMock()
        mock_build.return_value = mock_index
        
        # First call
        result1 = get_cached_index("https://example.com/test.zip")
        # Second call with same URL
        result2 = get_cached_index("https://example.com/test.zip")
        
        assert result1 == result2
        # Should only download/extract/build once
        assert mock_download.call_count == 1
        assert mock_extract.call_count == 1
        assert mock_build.call_count == 1
    
    @patch('search.download_zip')
    @patch('search.extract_md_files')
    @patch('search.build_index')
    def test_get_cached_index_different_urls(self, mock_build, mock_extract, mock_download):
        """Test that different URLs create separate cache entries."""
        mock_download.return_value = "/path/to/file.zip"
        mock_extract.return_value = [{"filename": "test.md", "content": "content"}]
        mock_build.return_value = MagicMock()
        
        get_cached_index("https://example.com/repo1.zip")
        get_cached_index("https://example.com/repo2.zip")
        
        assert mock_download.call_count == 2
        assert mock_extract.call_count == 2
        assert mock_build.call_count == 2
    
    @patch('search.download_zip')
    @patch('search.extract_md_files')
    @patch('search.build_index')
    def test_get_cached_index_custom_dest_dir(self, mock_build, mock_extract, mock_download):
        """Test that custom dest_dir is passed to download_zip."""
        mock_download.return_value = "/custom/path/file.zip"
        mock_extract.return_value = [{"filename": "test.md", "content": "content"}]
        mock_build.return_value = MagicMock()
        
        get_cached_index("https://example.com/test.zip", dest_dir="/custom/path")
        
        mock_download.assert_called_once_with("https://example.com/test.zip", "/custom/path")
    
    # --- Unhappy Path Tests ---
    
    @patch('search.download_zip')
    def test_get_cached_index_download_error(self, mock_download):
        """Test that download errors propagate correctly."""
        mock_download.side_effect = DownloadError("Connection failed")
        
        with pytest.raises(DownloadError, match="Connection failed"):
            get_cached_index("https://example.com/test.zip")
    
    @patch('search.download_zip')
    @patch('search.extract_md_files')
    def test_get_cached_index_extraction_error(self, mock_extract, mock_download):
        """Test that extraction errors propagate correctly."""
        mock_download.return_value = "/path/to/file.zip"
        mock_extract.side_effect = ExtractionError("Invalid zip")
        
        with pytest.raises(ExtractionError, match="Invalid zip"):
            get_cached_index("https://example.com/test.zip")
    
    @patch('search.download_zip')
    @patch('search.extract_md_files')
    @patch('search.build_index')
    def test_get_cached_index_indexing_error(self, mock_build, mock_extract, mock_download):
        """Test that indexing errors propagate correctly."""
        mock_download.return_value = "/path/to/file.zip"
        mock_extract.return_value = []
        mock_build.side_effect = IndexingError("Cannot build index from empty document list")
        
        with pytest.raises(IndexingError, match="Cannot build index from empty"):
            get_cached_index("https://example.com/test.zip")
    
    @patch('search.download_zip')
    def test_get_cached_index_invalid_url(self, mock_download):
        """Test that invalid URL raises ValueError."""
        mock_download.side_effect = ValueError("Invalid URL")
        
        with pytest.raises(ValueError, match="Invalid URL"):
            get_cached_index("not-a-valid-url")


class TestIntegration:
    """Integration tests with real files."""
    
    def teardown_method(self):
        """Clear the cache after each test."""
        _index_cache.clear()
    
    @pytest.mark.integration
    @patch('search.download_zip')
    def test_full_workflow(self, mock_download, tmp_path):
        """Test the complete workflow using get_cached_index."""
        # Create a test zip file
        zip_path = tmp_path / "test_docs.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("project-main/docs/demo.md", "# Demo\nThis is a demo document showing features")
            zf.writestr("project-main/docs/guide.md", "# Guide\nA comprehensive user guide")
            zf.writestr("project-main/README.md", "# Project\nProject overview and demo")
        
        # Mock download_zip to return our local file
        mock_download.return_value = str(zip_path)
        
        # Use get_cached_index with a dummy URL
        dummy_url = "https://example.com/test_docs.zip"
        index = get_cached_index(dummy_url)
        
        # Verify index was built and cached
        assert index is not None
        assert dummy_url in _index_cache
        
        # Search
        results = search(index, "demo", num_results=5)
        assert len(results) > 0
        
        # Verify demo-related docs are in results
        filenames = [r['filename'] for r in results]
        assert any("demo" in f.lower() or "readme" in f.lower() for f in filenames)

        # Verify download was called
        mock_download.assert_called_once_with(dummy_url, ".")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
