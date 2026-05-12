from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages
import operator

class ResearchState(TypedDict):
    """State schema for the research agent"""
    messages: Annotated[list, add_messages]  # Chat history
    search_queries: Annotated[List[str], operator.add]  # Accumulating search queries
    search_results: Annotated[List[Dict[str, Any]], operator.add]  # Accumulating search results
    research_loop_count: int  # Simple counter to track loops
    is_information_sufficient: bool  # Flag to control flow
    final_answer: str  # Final answer
    error_count: int  # Error tracking
    metadata: Dict[str, Any]  # Additional metadata