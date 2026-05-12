
import pytest
from app.agent.graph import ResearchAgent

@pytest.mark.asyncio
async def test_agent_basic_query():
    agent = ResearchAgent()
    result = await agent.process_message(
        "What is the capital of France?",
        "test_thread_1"
    )
    assert "Paris" in result["final_answer"]
    assert len(result["search_queries"]) > 0
