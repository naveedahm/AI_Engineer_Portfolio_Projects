from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import GoogleSearchAPIWrapper
from app.core.config import settings
import asyncio
from typing import List, Dict, Any

class SearchTool:
    def __init__(self):
        if settings.SEARCH_PROVIDER == "duckduckgo":
            self.search = DuckDuckGoSearchRun()
        elif settings.SEARCH_PROVIDER == "google":
            self.search = GoogleSearchAPIWrapper()
        else:
            raise ValueError(f"Unknown search provider: {settings.SEARCH_PROVIDER}")
    
    async def search_multiple(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple searches concurrently"""
        tasks = [self._search_single(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            {"query": queries[i], "result": str(r) if not isinstance(r, Exception) else f"Error: {str(r)}"}
            for i, r in enumerate(results)
        ]
    
    async def _search_single(self, query: str) -> str:
        """Execute a single search"""
        # Run in thread pool since some search APIs are synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.search.run, query)
        return result[:1000]  # Limit result size