"""
Documentation search module using minsearch.

This module provides functionality to:
1. Download a zip file from a URL
2. Extract markdown (.md, .mdx) files from the zip
3. Build a search index using minsearch
4. Search the index for relevant documents
"""

import os
import zipfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests
from minsearch import Index


class SearchError(Exception):
    """Base exception for search-related errors."""
    pass


class DownloadError(SearchError):
    """Raised when there's an error downloading a file."""
    pass


class IndexingError(SearchError):
    """Raised when there's an error building the search index."""
    pass


class ExtractionError(SearchError):
    """Raised when there's an error extracting files from zip."""
    pass


def download_zip(url: str, dest_dir: str = ".", timeout: int = 60) -> str:
    """
    Download a zip file from a URL if it doesn't already exist.
    
    Args:
        url: The URL of the zip file to download.
        dest_dir: The destination directory to save the file.
        timeout: Request timeout in seconds.
        
    Returns:
        The path to the downloaded (or existing) zip file.
        
    Raises:
        DownloadError: If the download fails.
        ValueError: If the URL is invalid.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    parsed = urlparse(url)
    if not all([parsed.scheme in ('http', 'https'), parsed.netloc]):
        raise ValueError(f"Invalid URL: {url}")
    
    # Extract filename from URL
    filename = os.path.basename(parsed.path)
    if not filename.endswith('.zip'):
        filename = "download.zip"
    
    dest_path = os.path.join(dest_dir, filename)
    
    # Skip download if file already exists
    if os.path.exists(dest_path):
        return dest_path
    
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Ensure destination directory exists
        os.makedirs(dest_dir, exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return dest_path
    
    except requests.exceptions.Timeout:
        raise DownloadError(f"Download timed out after {timeout} seconds")
    except requests.exceptions.ConnectionError as e:
        raise DownloadError(f"Connection error: {str(e)}")
    except requests.exceptions.HTTPError as e:
        raise DownloadError(f"HTTP error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise DownloadError(f"Download failed: {str(e)}")
    except IOError as e:
        raise DownloadError(f"Failed to save file: {str(e)}")


def extract_md_files(zip_path: str) -> List[dict]:
    """
    Extract markdown files (.md, .mdx) from a zip file.
    
    The first part of the path (e.g., 'fastmcp-main/') is removed from filenames.
    
    Args:
        zip_path: Path to the zip file.
        
    Returns:
        A list of dictionaries with 'filename' and 'content' keys.
        
    Raises:
        ExtractionError: If the zip file is invalid or cannot be read.
        ValueError: If the zip path is invalid.
    """
    if not zip_path or not isinstance(zip_path, str):
        raise ValueError("Zip path must be a non-empty string")
    
    if not os.path.exists(zip_path):
        raise ExtractionError(f"Zip file not found: {zip_path}")
    
    documents = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for file_info in zf.infolist():
                # Skip directories
                if file_info.is_dir():
                    continue
                
                filename = file_info.filename
                
                # Only process .md and .mdx files
                if not (filename.endswith('.md') or filename.endswith('.mdx')):
                    continue
                
                # Remove the first part of the path (e.g., 'fastmcp-main/')
                parts = filename.split('/', 1)
                if len(parts) > 1:
                    clean_filename = parts[1]
                else:
                    clean_filename = filename
                
                # Skip if the cleaned filename is empty
                if not clean_filename:
                    continue
                
                try:
                    content = zf.read(file_info).decode('utf-8')
                    documents.append({
                        'filename': clean_filename,
                        'content': content
                    })
                except UnicodeDecodeError:
                    # Skip files that can't be decoded as UTF-8
                    continue
    
    except zipfile.BadZipFile:
        raise ExtractionError(f"Invalid or corrupted zip file: {zip_path}")
    except IOError as e:
        raise ExtractionError(f"Failed to read zip file: {str(e)}")
    
    return documents


def build_index(documents: List[dict]) -> Index:
    """
    Build a minsearch Index from a list of documents.
    
    Args:
        documents: A list of dictionaries with 'filename' and 'content' keys.
        
    Returns:
        A minsearch Index object.
        
    Raises:
        IndexingError: If the index cannot be built.
        ValueError: If documents is invalid.
    """
    if documents is None:
        raise ValueError("Documents cannot be None")
    
    if not isinstance(documents, list):
        raise ValueError("Documents must be a list")
    
    if len(documents) == 0:
        raise IndexingError("Cannot build index from empty document list")
    
    try:
        index = Index(
            text_fields=["content"],
            keyword_fields=["filename"]
        )
        index.fit(documents)
        return index
    except Exception as e:
        raise IndexingError(f"Failed to build index: {str(e)}")


def search(index: Index, query: str, num_results: int = 5) -> List[dict]:
    """
    Search the index for documents matching the query.
    
    Args:
        index: The minsearch Index to search.
        query: The search query string.
        num_results: Maximum number of results to return (default: 5).
        
    Returns:
        A list of matching documents, each with 'filename' and 'content' keys.
        
    Raises:
        ValueError: If the query is invalid or index is None.
        SearchError: If the search fails.
    """
    if index is None:
        raise ValueError("Index cannot be None")
    
    if not isinstance(query, str):
        raise ValueError("Query must be a string")
    
    if not query.strip():
        raise ValueError("Query cannot be empty or whitespace only")
    
    if not isinstance(num_results, int) or num_results <= 0:
        raise ValueError("num_results must be a positive integer")
    
    try:
        results = index.search(query, num_results=num_results)
        return results
    except Exception as e:
        raise SearchError(f"Search failed: {str(e)}")


# Global index cache for documentation (keyed by zip URL)
_index_cache: dict = {}


def get_cached_index(zip_url: str, dest_dir: str = ".") -> Index:
    """
    Get or create a cached documentation index for a zip URL.
    
    Downloads the zip if needed, extracts markdown files, and builds
    a search index. Subsequent calls with the same URL return the
    cached index.
    
    Args:
        zip_url: URL to the GitHub zip file.
        dest_dir: Directory to save downloaded zip files.
        
    Returns:
        A minsearch Index object.
    """
    if zip_url not in _index_cache:
        zip_path = download_zip(zip_url, dest_dir)
        documents = extract_md_files(zip_path)
        _index_cache[zip_url] = build_index(documents)
    return _index_cache[zip_url]


if __name__ == "__main__":
    # Example usage
    FASTMCP_ZIP_URL = "https://github.com/jlowin/fastmcp/archive/refs/heads/main.zip"
    
    print("Downloading FastMCP docs...")
    zip_path = download_zip(FASTMCP_ZIP_URL)
    print(f"Zip file: {zip_path}")
    
    print("\nExtracting markdown files...")
    documents = extract_md_files(zip_path)
    print(f"Found {len(documents)} markdown files")
    
    print("\nBuilding search index...")
    index = build_index(documents)
    
    print("\nSearching for 'demo'...")
    results = search(index, "demo", num_results=5)
    
    print(f"\nTop {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['filename']}")
