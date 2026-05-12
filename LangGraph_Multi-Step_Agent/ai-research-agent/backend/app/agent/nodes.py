from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.state import ResearchState
from app.agent.tools import SearchTool
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class AgentNodes:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
        self.search_tool = SearchTool()
    
    async def generate_queries(self, state: ResearchState) -> Dict[str, Any]:
        """Generate search queries based on conversation"""
        logger.info("Generating search queries")
        
        # Get the last user message
        last_message = next(
            (msg for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            None
        )
        
        if not last_message:
            return {"search_queries": []}
        
        prompt = f"""Based on the following user question, generate 2-3 specific web search queries.
        Return ONLY a JSON list of strings, no other text.
        
        Question: {last_message.content}
        
        Example output: ["query 1", "query 2", "query 3"]
        """
        
        try:
            response = await self.llm.ainvoke(prompt)
            queries = json.loads(response.content.strip())
            if not isinstance(queries, list):
                queries = [last_message.content]
        except Exception as e:
            logger.error(f"Failed to parse queries: {e}")
            queries = [last_message.content]
        
        return {"search_queries": queries}
    
    async def execute_search(self, state: ResearchState) -> Dict[str, Any]:
        """Execute all search queries"""
        logger.info(f"Executing {len(state['search_queries'])} searches")
        
        results = await self.search_tool.search_multiple(state["search_queries"])
        
        return {
            "search_results": results,
            "research_loop_count": state.get("research_loop_count", 0) + 1
        }
    
    async def reflect_on_results(self, state: ResearchState) -> Dict[str, Any]:
        """Determine if we have enough information"""
        logger.info("Reflecting on search results")
        
        # Combine all search results
        context = "\n\n".join([
            f"Search {i+1} ({r['query']}):\n{r['result']}"
            for i, r in enumerate(state["search_results"])
        ])
        
        last_message = next(
            (msg for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            None
        )
        
        prompt = f"""You are evaluating if you have enough information to answer the user's question.
        
        User Question: {last_message.content if last_message else "Unknown"}
        
        Information gathered so far:
        {context}
        
        Research attempt: {state.get('research_loop_count', 0)}/3
        
        Answer with EXACTLY one word: 'yes' if you can answer the question completely, or 'no' if you need more information.
        """
        
        response = await self.llm.ainvoke(prompt)
        is_sufficient = "yes" in response.content.lower()
        
        # Also check loop count limit
        if state.get("research_loop_count", 0) >= 3:
            is_sufficient = True
            logger.info("Max research loops reached, forcing final answer")
        
        return {"is_information_sufficient": is_sufficient}
    
    async def finalize_answer(self, state: ResearchState) -> Dict[str, Any]:
        """Generate the final answer"""
        logger.info("Generating final answer")
        
        # Combine all gathered information
        context = "\n\n".join([
            f"Source {i+1} ({r['query']}):\n{r['result']}"
            for i, r in enumerate(state["search_results"])
        ])
        
        last_message = next(
            (msg for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            None
        )
        
        prompt = f"""Write a comprehensive, well-structured answer to the user's question.
        Use ONLY the information provided in the context. If the context doesn't contain enough information, state that clearly.
        
        Question: {last_message.content if last_message else "Unknown"}
        
        Context:
        {context}
        
        Instructions:
        1. Start with a clear summary
        2. Organize information logically
        3. Cite sources when possible
        4. Be specific and factual
        5. If information is missing, say so
        
        Answer:
        """
        
        response = await self.llm.ainvoke(prompt)
        
        return {"final_answer": response.content}