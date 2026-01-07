"""
Comprehensive test suite for the web scraping tool.

Tests cover:
- Happy paths: successful scraping
- Unhappy paths: invalid URLs, network errors, timeout handling
"""

import pytest
from unittest.mock import patch, Mock
import requests

from scrape_web import (
    scrape_web,
    validate_url,
    WebScraperError,
    InvalidURLError,
    NetworkError,
    ContentFetchError,
)


class TestValidateUrl:
    """Tests for URL validation function."""
    
    def test_valid_http_url(self):
        """Test that HTTP URLs are valid."""
        assert validate_url("http://example.com") is True
    
    def test_valid_https_url(self):
        """Test that HTTPS URLs are valid."""
        assert validate_url("https://example.com") is True
    
    def test_valid_url_with_path(self):
        """Test URL with path is valid."""
        assert validate_url("https://example.com/path/to/page") is True
    
    def test_valid_url_with_query_params(self):
        """Test URL with query parameters is valid."""
        assert validate_url("https://example.com?foo=bar&baz=qux") is True
    
    def test_invalid_empty_string(self):
        """Test that empty string is invalid."""
        assert validate_url("") is False
    
    def test_invalid_none(self):
        """Test that None is invalid."""
        assert validate_url(None) is False
    
    def test_invalid_no_scheme(self):
        """Test that URL without scheme is invalid."""
        assert validate_url("example.com") is False
    
    def test_invalid_ftp_scheme(self):
        """Test that FTP scheme is invalid."""
        assert validate_url("ftp://example.com") is False
    
    def test_invalid_just_scheme(self):
        """Test that just scheme is invalid."""
        assert validate_url("https://") is False
    
    def test_invalid_non_string(self):
        """Test that non-string input is invalid."""
        assert validate_url(12345) is False
        assert validate_url(["https://example.com"]) is False


class TestScrapeWeb:
    """Tests for the main scrape_web function."""
    
    # --- Happy Path Tests ---
    
    @patch('scrape_web.requests.get')
    def test_successful_scrape(self, mock_get):
        """Test successful content scraping."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Hello World\n\nThis is markdown content."
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = scrape_web("https://example.com")
        
        assert result == "# Hello World\n\nThis is markdown content."
        mock_get.assert_called_once_with(
            "https://r.jina.ai/https://example.com",
            timeout=30
        )
    
    @patch('scrape_web.requests.get')
    def test_successful_scrape_with_custom_timeout(self, mock_get):
        """Test scraping with custom timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = scrape_web("https://example.com", timeout=60)
        
        mock_get.assert_called_once_with(
            "https://r.jina.ai/https://example.com",
            timeout=60
        )
    
    @patch('scrape_web.requests.get')
    def test_successful_scrape_with_complex_url(self, mock_get):
        """Test scraping URL with path and query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = "https://example.com/path/to/page?foo=bar"
        result = scrape_web(url)
        
        mock_get.assert_called_once_with(
            f"https://r.jina.ai/{url}",
            timeout=30
        )
    
    # --- Unhappy Path Tests ---
    
    def test_invalid_url_empty(self):
        """Test that empty URL raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid URL provided"):
            scrape_web("")
    
    def test_invalid_url_none(self):
        """Test that None URL raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid URL provided"):
            scrape_web(None)
    
    def test_invalid_url_no_scheme(self):
        """Test that URL without scheme raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid URL provided"):
            scrape_web("example.com")
    
    def test_invalid_url_malformed(self):
        """Test that malformed URL raises InvalidURLError."""
        with pytest.raises(InvalidURLError, match="Invalid URL provided"):
            scrape_web("not-a-valid-url")
    
    def test_invalid_timeout_zero(self):
        """Test that zero timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be a positive number"):
            scrape_web("https://example.com", timeout=0)
    
    def test_invalid_timeout_negative(self):
        """Test that negative timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be a positive number"):
            scrape_web("https://example.com", timeout=-5)
    
    def test_invalid_timeout_string(self):
        """Test that string timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be a positive number"):
            scrape_web("https://example.com", timeout="30")
    
    @patch('scrape_web.requests.get')
    def test_timeout_error(self, mock_get):
        """Test that request timeout raises NetworkError."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        with pytest.raises(NetworkError, match="Request timed out"):
            scrape_web("https://example.com")
    
    @patch('scrape_web.requests.get')
    def test_connection_error(self, mock_get):
        """Test that connection error raises NetworkError."""
        mock_get.side_effect = requests.exceptions.ConnectionError("No connection")
        
        with pytest.raises(NetworkError, match="Connection error"):
            scrape_web("https://example.com")
    
    @patch('scrape_web.requests.get')
    def test_http_404_error(self, mock_get):
        """Test that HTTP 404 raises ContentFetchError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
        mock_get.return_value = mock_response
        
        with pytest.raises(ContentFetchError, match="HTTP error 404"):
            scrape_web("https://example.com/nonexistent")
    
    @patch('scrape_web.requests.get')
    def test_http_500_error(self, mock_get):
        """Test that HTTP 500 raises ContentFetchError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error")
        mock_get.return_value = mock_response
        
        with pytest.raises(ContentFetchError, match="HTTP error 500"):
            scrape_web("https://example.com")
    
    @patch('scrape_web.requests.get')
    def test_generic_request_exception(self, mock_get):
        """Test that generic RequestException raises WebScraperError."""
        mock_get.side_effect = requests.exceptions.RequestException("Something went wrong")
        
        with pytest.raises(WebScraperError, match="Request failed"):
            scrape_web("https://example.com")


class TestIntegration:
    """Integration tests that make actual HTTP requests."""
    
    @pytest.mark.integration
    def test_real_scrape_datatalks(self):
        """Integration test: scrape datatalks.club."""
        content = scrape_web("https://datatalks.club")
        assert len(content) > 0
        assert isinstance(content, str)
    
    @pytest.mark.integration
    def test_real_scrape_github_minsearch(self):
        """Integration test: scrape github minsearch repo."""
        content = scrape_web("https://github.com/alexeygrigorev/minsearch")
        assert len(content) > 0
        assert isinstance(content, str)
        # Print character count for reference
        print(f"\nMinsearch page character count: {len(content)}")


if __name__ == "__main__":
    # Run integration tests
    print("Running integration test for minsearch GitHub page...")
    try:
        content = scrape_web("https://github.com/alexeygrigorev/minsearch")
        print(f"Successfully scraped the page!")
        print(f"Character count: {len(content)}")
        print(f"\n--- First 1000 characters ---\n")
        print(content[:1000])
    except WebScraperError as e:
        print(f"Error: {e}")
