"""
Web scraping tool using Jina Reader to download web page content as markdown.

To use Jina Reader, prepend 'https://r.jina.ai/' to any URL to get the content
in markdown format.
"""

import requests
from urllib.parse import urlparse


class WebScraperError(Exception):
    """Base exception for web scraping errors."""
    pass


class InvalidURLError(WebScraperError):
    """Raised when the provided URL is invalid."""
    pass


class NetworkError(WebScraperError):
    """Raised when there's a network-related error."""
    pass


class ContentFetchError(WebScraperError):
    """Raised when the content cannot be fetched."""
    pass


def validate_url(url: str) -> bool:
    """
    Validate if the provided string is a valid URL.
    
    Args:
        url: The URL string to validate.
        
    Returns:
        True if the URL is valid, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        result = urlparse(url)
        # Must have scheme (http/https) and netloc (domain)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def scrape_web(url: str, timeout: int = 30) -> str:
    """
    Scrape the content of a web page using Jina Reader.
    
    This function uses the Jina Reader service (r.jina.ai) to fetch
    the content of a web page and return it in markdown format.
    
    Args:
        url: The URL of the web page to scrape.
        timeout: Request timeout in seconds (default: 30).
        
    Returns:
        The content of the web page in markdown format.
        
    Raises:
        ValueError: If timeout is not a positive number.
        InvalidURLError: If the provided URL is invalid.
        NetworkError: If there's a network-related error.
        ContentFetchError: If the content cannot be fetched.
        WebScraperError: For other generic scraping errors.
    """
    # Validate the URL
    if not validate_url(url):
        raise InvalidURLError(f"Invalid URL provided: {url}")
    
    # Validate timeout
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("Timeout must be a positive number")
    
    # Construct the Jina Reader URL
    jina_url = f"https://r.jina.ai/{url}"
    
    try:
        response = requests.get(jina_url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        raise NetworkError(f"Request timed out after {timeout} seconds")
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(f"Connection error: {str(e)}")
    except requests.exceptions.HTTPError as e:
        raise ContentFetchError(f"HTTP error {response.status_code}: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise WebScraperError(f"Request failed: {str(e)}")


if __name__ == "__main__":
    # Example usage
    test_url = "https://github.com/alexeygrigorev/minsearch"
    try:
        content = scrape_web(test_url)
        print(f"Successfully scraped {len(content)} characters from {test_url}")
        print("\n--- First 500 characters ---\n")
        print(content[:500])
    except WebScraperError as e:
        print(f"Error: {e}")
