from fastmcp import FastMCP
from scrape_web import scrape_web as scrape_web_func, WebScraperError
from search import (
    get_cached_index,
    search as search_index,
    SearchError,
)

mcp = FastMCP("Documentation Search Engine")


@mcp.tool
def scrape_web(url: str) -> str:
    """
    Scrape the content of a web page using Jina Reader.
    
    This tool fetches the content of any web page and returns it
    in markdown format using the Jina Reader service.
    
    Args:
        url: The URL of the web page to scrape (must be http or https).
        
    Returns:
        The content of the web page in markdown format.
    """
    return scrape_web_func(url)


@mcp.tool
def count_word_occurrences(url: str, word: str, case_insensitive: bool = True) -> dict:
    """
    Count occurrences of a specific word on a web page.
    
    This tool scrapes a web page and counts how many times
    a specific word appears in the content.
    
    Args:
        url: The URL of the web page to analyze.
        word: The word to search for and count.
        case_insensitive: If True, count is case-insensitive (default: True).
        
    Returns:
        A dictionary with the count and additional info.
    """
    content = scrape_web_func(url)
    
    if case_insensitive:
        search_content = content.lower()
        search_word = word.lower()
    else:
        search_content = content
        search_word = word
    
    count = search_content.count(search_word)
    
    return {
        "word": word,
        "count": count,
        "case_insensitive": case_insensitive,
        "url": url,
        "content_length": len(content)
    }


@mcp.tool
def search_docs(
    query: str,
    zip_url: str = "https://github.com/jlowin/fastmcp/archive/refs/heads/main.zip",
    num_results: int = 5
) -> list:
    """
    Search documentation from a GitHub repository zip file.
    
    This tool downloads documentation from a GitHub repository (as a zip),
    indexes the markdown files, and returns the most relevant documents
    matching the query. The index is cached for subsequent searches.
    
    Args:
        query: The search query string.
        zip_url: URL to the GitHub zip file (default: FastMCP docs).
                 Format: https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip
        num_results: Maximum number of results to return (default: 5).
        
    Returns:
        A list of matching documents with filename and content preview.
        
    Examples:
        # Search FastMCP docs (default)
        search_docs("demo")
        
        # Search minsearch docs
        search_docs("index", zip_url="https://github.com/alexeygrigorev/minsearch/archive/refs/heads/main.zip")
    """
    index = get_cached_index(zip_url)
    results = search_index(index, query, num_results=num_results)
    
    # Return simplified results with filename and content preview
    return [
        {
            "filename": doc["filename"],
            "content_preview": doc["content"][:500] + "..." if len(doc["content"]) > 500 else doc["content"]
        }
        for doc in results
    ]


if __name__ == "__main__":
    mcp.run()

