"""
Search Processor for Feishu MCP

Handles search result responses with pagination support.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Single search result"""
    title: str
    url: str
    result_type: str  # "document" or "wiki"
    owner: str
    node_token: Optional[str] = None  # For wiki


@dataclass
class SearchResults:
    """Complete search response"""
    items: List[SearchResult]
    has_more: bool
    page_token: Optional[str]
    total_count: int


class SearchProcessor:
    """
    Process search results from Feishu MCP.

    Search responses include:
    - items: Array of search results
    - has_more: Whether more results exist
    - page_token: Token for pagination
    """

    def __init__(self, cache_dir: str = "/tmp/feishu_mcp_cache"):
        """
        Initialize search processor.

        Args:
            cache_dir: Directory to cache search results
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse_response(self, response: Dict) -> SearchResults:
        """
        Parse search response from Feishu MCP.

        Args:
            response: Raw response from search_feishu_documents

        Returns:
            SearchResults with parsed data
        """
        # Handle both document and wiki results
        items = []

        # Document results
        document_items = response.get("data", {}).get("items", [])
        for item in document_items:
            items.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                result_type="document",
                owner=item.get("owner", "")
            ))

        # Wiki results (if present)
        wiki_items = response.get("items", [])
        for item in wiki_items:
            items.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                result_type="wiki",
                owner=item.get("owner", ""),
                node_token=item.get("node_token")
            ))

        return SearchResults(
            items=items,
            has_more=response.get("has_more", False),
            page_token=response.get("page_token"),
            total_count=len(items)
        )

    def format_results(self, results: SearchResults,
                      show_numbers: bool = True) -> str:
        """
        Format search results for display.

        Args:
            results: Parsed search results
            show_numbers: Whether to show result numbers

        Returns:
            Formatted string
        """
        if not results.items:
            return "No results found."

        lines = [f"Found {results.total_count} result(s):\n"]

        for i, item in enumerate(results.items, 1):
            prefix = f"{i}. " if show_numbers else ""
            icon = "📄" if item.result_type == "document" else "📚"
            lines.append(f"{prefix}{icon} **{item.title}**")
            lines.append(f"   Type: {item.result_type}")
            lines.append(f"   URL: {item.url}")
            if item.owner:
                lines.append(f"   Owner: {item.owner}")
            lines.append("")

        if results.has_more:
            lines.append("(More results available - use page_token to get next page)")

        return "\n".join(lines)

    def save_results(self, results: SearchResults,
                    query: str) -> Path:
        """
        Save search results to file.

        Args:
            results: Parsed search results
            query: Search query for filename

        Returns:
            Path to saved file
        """
        import hashlib
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        filename = f"search_{query_hash}.json"
        filepath = self.cache_dir / filename

        data = {
            "query": query,
            "count": results.total_count,
            "has_more": results.has_more,
            "page_token": results.page_token,
            "items": [
                {
                    "title": item.title,
                    "url": item.url,
                    "type": item.result_type,
                    "owner": item.owner
                }
                for item in results.items
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath

    def get_next_page_params(self, results: SearchResults) -> Optional[Dict]:
        """
        Get parameters for fetching next page.

        Args:
            results: Current search results

        Returns:
            Dict with page_token if more results available
        """
        if not results.has_more or not results.page_token:
            return None

        return {"pageToken": results.page_token}
