from fastmcp import FastMCP
from scrape_web import scrape_web as scrape_web_func, WebScraperError

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


if __name__ == "__main__":
    mcp.run()
