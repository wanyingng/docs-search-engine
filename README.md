# Documentation Search Engine

A custom Model Context Protocol (MCP) server that acts as a documentation search engine.

This project attempts to build a simple, personal clone of [Context7](https://context7.com), unlocking the capability to access up-to-date documentation from GitHub repositories and web pages directly within your AI assistant's context.

## 🛠️ Tech Stack

- **Python**: Core programming language.
- **FastMCP**: Framework for building MCP servers easily.
- **minsearch**: Lightweight, in-memory full-text search engine.
- **uv**: Fast Python package and environment manager.
- **Jina Reader**: For turning web pages into LLM-friendly markdown.
- **requests**: For handling HTTP requests and downloading zip files.
- **pytest**: For comprehensive testing.

## 📂 Project Structure

```
docs-search-engine/
├── main.py             # Entry point: Defines MCP tools and server configuration
├── search.py           # Core logic: Zip download, extraction, indexing, and search
├── scrape_web.py       # Web scraping functionality (using Jina Reader)
├── test_search.py      # Tests for search functionality
├── test_scrape_web.py  # Tests for web scraping
└── pyproject.toml      # Project dependencies and configuration
```

## 🚀 Workflow

1.  **Ingestion**: The server downloads documentation source code (e.g., as a `.zip` from GitHub).
2.  **Indexing**: Markdown content (`.md` and `.mdx`) is extracted and indexed in-memory using `minsearch`.
3.  **Caching**: Indexes are cached by URL to ensure fast subsequent searches without re-downloading.
4.  **Retrieval**: Users query the system via MCP tools (`search_docs`, `scrape_web`), and relevant context is returned to the LLM.

## ⚙️ MCP Configuration

Add the following configuration to your MCP client settings (e.g., `mcp_config.json` in Google Antigravity):

```json
{
  "mcpServers": {
    "docs-search-engine": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:/Users/username/path/to/docs-search-engine",
        "main.py"
      ]
    }
  }
}
```

**Note**: Replace `C:/Users/username/path/to/docs-search-engine` with the actual absolute path to your project directory.

## 💡 Example Usage

Once the MCP server is connected to your AI assistant (e.g., VSCode, Claude, Cursor, Antigravity), you can use natural language to interact with it.

**1. Search Documentation**

```text
"Search for 'context' in the FastMCP docs."
```

```text
"Find information about 'indexing' in the minsearch docs (https://github.com/alexeygrigorev/minsearch)."
```

**2. Scrape Web Pages**

```text
"Scrape the content of https://example.com/blog/article and summarize it."
```

**3. Count Word Occurrences**

```text
"Count how many times the word 'LLM' appears on https://example.com/ai-trends."
```

## 💻 Setup & Execution

### Prerequisites

- Python 3.13+
- `uv` installed (recommended)

### Installation

1.  Clone the repository and navigate to the directory:

    ```bash
    cd docs-search-engine
    ```

2.  Install dependencies:
    ```bash
    uv sync
    ```

### Running Locally

To run the server manually for debugging:

```bash
uv run main.py
```

### Testing

Run the comprehensive test suite to ensure everything is working correctly:

```bash
# Run all tests
uv run pytest -v

# Run specific test files
uv run pytest test_search.py -v
uv run pytest test_scrape_web.py -v

# Run only integration tests
uv run pytest -m integration -v
```
