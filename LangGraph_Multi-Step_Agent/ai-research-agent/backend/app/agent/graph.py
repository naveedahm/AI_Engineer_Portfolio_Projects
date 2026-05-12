"""
LangGraph-based Research Agent with Real AI and Web Search
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agent.state import ResearchState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any, List, Literal
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ResearchAgent:
    def __init__(self):
        print("=" * 60)
        print("🤖 Initializing LangGraph Research Agent")
        print("=" * 60)
        
        # Initialize OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        self.use_real_ai = False
        
        if api_key and api_key != "your-openai-api-key-here" and api_key != "sk-proj-your-actual-openai-api-key-here":
            try:
                self.llm = ChatOpenAI(
                    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                    temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                    api_key=api_key
                )
                self.use_real_ai = True
                print(f"✅ OpenAI initialized: {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}")
            except Exception as e:
                print(f"❌ OpenAI initialization failed: {str(e)}")
                self.use_real_ai = False
        else:
            print("⚠️  No valid OpenAI API key found in .env file")
            print("   Current OPENAI_API_KEY value:", api_key[:20] + "..." if api_key else "Not set")
            print("   Running in demo mode. Add OPENAI_API_KEY to backend/.env for real AI responses")
        
        # Build the LangGraph
        self.graph = self._build_graph()
        self.checkpointer = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.checkpointer)
        print("✅ LangGraph compiled successfully")
        print("=" * 60)
    
    def _should_continue(self, state: ResearchState) -> Literal["continue", "end"]:
        is_sufficient = state.get("is_information_sufficient", False)
        loop_count = state.get("research_loop_count", 0)

        print(f"Decision check - Loop: {loop_count}/3, Sufficient: {is_sufficient}")

        if not is_sufficient and loop_count < 3:
            print("🔄 Decision: CONTINUE research")
            return "continue"
        else:
            print("✅ Decision: END research and finalize")
            return "end"


    async def process_message(self, message: str, thread_id: str) -> dict:
        print("\n" + "=" * 60)
        print(f"💬 Processing: {message[:100]}...")
        print(f"🆔 Thread: {thread_id}")
        print("=" * 60)

        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "messages": [HumanMessage(content=message)],
            "search_queries": [],
            "search_results": [],
            "research_loop_count": 0,
            "is_information_sufficient": False,
            "final_answer": "",
            "error_count": 0,
            "metadata": {},
        }

        try:
            final_state = await self.app.ainvoke(initial_state, config=config)

            print(
                f"\n✅ Answer generated "
                f"({len(final_state.get('final_answer', ''))} chars)"
            )

            return final_state

        except Exception as e:
            print(f"\n❌ Error: {str(e)}")

            return {
                "final_answer": f"Error: {str(e)}",
                "search_queries": [],
                "research_loop_count": 0,
                "messages": [],
            }


    async def stream_process(self, message: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "messages": [HumanMessage(content=message)],
            "search_queries": [],
            "search_results": [],
            "research_loop_count": 0,
            "is_information_sufficient": False,
            "final_answer": "",
            "error_count": 0,
            "metadata": {},
        }

        async for event in self.app.astream_events(
            initial_state,
            config=config,
            version="v1",
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content

                if chunk:
                    yield {
                        "type": "token",
                        "content": chunk,
                    }

            elif event["event"] == "on_chain_end":
                output = event["data"].get("output", {})

                if "final_answer" in output:
                    yield {
                        "type": "final",
                        "content": output["final_answer"],
                    }


    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        builder = StateGraph(ResearchState)
        
        # Add nodes
        builder.add_node("generate_queries", self._generate_queries)
        builder.add_node("execute_search", self._execute_search)
        builder.add_node("reflect_on_results", self._reflect_on_results)
        builder.add_node("finalize_answer", self._finalize_answer)
        
        # Add edges
        builder.set_entry_point("generate_queries")
        builder.add_edge("generate_queries", "execute_search")
        builder.add_edge("execute_search", "reflect_on_results")
        
        # Conditional routing - use lambda to call instance method
        builder.add_conditional_edges(
            "reflect_on_results",
            self._should_continue,  # This is now a method reference
            {
                "continue": "generate_queries",
                "end": "finalize_answer"
            }
        )
        
        builder.add_edge("finalize_answer", END)
        
        return builder
    
    async def _generate_queries(self, state: ResearchState) -> Dict[str, Any]:
        """Generate search queries based on user question"""
        print("\n🔍 NODE: Generating Search Queries")
        
        # Get the last user message
        last_message = None
        messages = state.get("messages", [])
        
        # Handle both dictionary and object messages
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                last_message = msg
                break
            elif isinstance(msg, dict) and msg.get('type') == 'human':
                last_message = msg
                break
            elif isinstance(msg, HumanMessage):
                last_message = msg
                break
        
        if not last_message:
            print("   No user message found")
            return {"search_queries": []}
        
        # Extract content
        user_question = last_message.content if hasattr(last_message, 'content') else last_message.get('content', '')
        print(f"   Question: {user_question[:100]}...")
        
        if self.use_real_ai:
            # Use real AI to generate search queries
            prompt = f"""Generate 2-3 specific web search queries to thoroughly answer the following question.
            Return ONLY a JSON list of strings, no other text.
            
            Question: {user_question}
            
            Example output: ["query 1", "query 2", "query 3"]
            """
            
            try:
                response = await self.llm.ainvoke(prompt)
                # Extract JSON from response
                content = response.content.strip()
                # Try to parse JSON
                if content.startswith('['):
                    queries = json.loads(content)
                else:
                    # Try to extract JSON array
                    import re
                    match = re.search(r'\[.*\]', content, re.DOTALL)
                    if match:
                        queries = json.loads(match.group())
                    else:
                        queries = [user_question]
                
                print(f"📝 Generated queries: {queries}")
                return {"search_queries": queries}
            except Exception as e:
                print(f"❌ Error generating queries: {str(e)}")
                return {"search_queries": [user_question]}
        else:
            # Demo mode: generate mock queries
            print("📝 Demo mode: using question as query")
            return {"search_queries": [user_question]}
    
    async def _execute_search(self, state: ResearchState) -> Dict[str, Any]:
        """Execute web searches"""
        print("\n🌐 NODE: Executing Web Searches")
        
        search_queries = state.get("search_queries", [])
        search_results = []
        
        if not search_queries:
            print("   No search queries to execute")
            return {"search_results": [], "research_loop_count": state.get("research_loop_count", 0) + 1}
        
        for query in search_queries:
            print(f"   🔍 Searching: {query}")
            
            if self.use_real_ai:
                # Perform real web search
                try:
                    from duckduckgo_search import DDGS
                    
                    with DDGS() as ddgs:
                        results = list(ddgs.text(query, max_results=3))
                        if results:
                            result_text = "\n".join([f"- {r['body'][:500]}" for r in results[:3]])
                            search_results.append({
                                "query": query,
                                "result": result_text
                            })
                            print(f"   ✅ Found {len(results)} results")
                        else:
                            search_results.append({
                                "query": query,
                                "result": "No results found."
                            })
                            print(f"   ⚠️ No results found")
                except ImportError:
                    print("   ❌ DuckDuckGo search not installed")
                    search_results.append({
                        "query": query,
                        "result": "Web search not available. Install: pip install duckduckgo-search"
                    })
                except Exception as e:
                    print(f"   ❌ Search error: {str(e)}")
                    search_results.append({
                        "query": query,
                        "result": f"Search error: {str(e)}"
                    })
            else:
                # Demo mode: mock results
                print("   📝 Demo mode: mock search result")
                search_results.append({
                    "query": query,
                    "result": f"Demo search result for: '{query}'. Enable OpenAI API key and install duckduckgo-search for real web search."
                })
        
        research_loop_count = state.get("research_loop_count", 0) + 1
        
        return {
            "search_results": search_results,
            "research_loop_count": research_loop_count
        }
    
    async def _reflect_on_results(self, state: ResearchState) -> Dict[str, Any]:
        """Determine if we have enough information"""
        print("\n🤔 NODE: Reflecting on Results")
        
        research_loop_count = state.get("research_loop_count", 0)
        search_results = state.get("search_results", [])
        
        # Get the last user message
        last_message = None
        messages = state.get("messages", [])
        
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                last_message = msg
                break
            elif isinstance(msg, dict) and msg.get('type') == 'human':
                last_message = msg
                break
            elif isinstance(msg, HumanMessage):
                last_message = msg
                break
        
        if not last_message:
            print("   No user message found")
            return {"is_information_sufficient": True}
        
        user_question = last_message.content if hasattr(last_message, 'content') else last_message.get('content', '')
        
        # If we've done too many loops, stop
        if research_loop_count >= 3:
            print(f"   Max research loops reached ({research_loop_count}/3), stopping")
            return {"is_information_sufficient": True}
        
        # If no search results, stop
        if not search_results:
            print("   No search results available, stopping")
            return {"is_information_sufficient": True}
        
        if self.use_real_ai:
            # Use AI to decide if we have enough information
            context = "\n".join([r.get("result", "") for r in search_results[:2]])
            
            prompt = f"""Based on the search results, determine if you have enough information to answer the user's question.
            
            User Question: {user_question}
            
            Search Results:
            {context[:1500]}
            
            Answer with ONLY 'yes' if you can answer the question completely, or 'no' if you need more information.
            """
            
            try:
                response = await self.llm.ainvoke(prompt)
                is_sufficient = "yes" in response.content.lower()
                print(f"   AI decision: {'Sufficient' if is_sufficient else 'Insufficient'}")
                return {"is_information_sufficient": is_sufficient}
            except Exception as e:
                print(f"   ❌ Error in reflection: {str(e)}")
                return {"is_information_sufficient": True}
        else:
            # Demo mode: stop after first iteration
            print("   Demo mode: stopping after first iteration")
            return {"is_information_sufficient": True}
    
    async def _finalize_answer(self, state: ResearchState) -> Dict[str, Any]:
        """Generate the final answer"""
        print("\n📝 NODE: Finalizing Answer")
        
        # Get the last user message
        last_message = None
        messages = state.get("messages", [])
        
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                last_message = msg
                break
            elif isinstance(msg, dict) and msg.get('type') == 'human':
                last_message = msg
                break
            elif isinstance(msg, HumanMessage):
                last_message = msg
                break
        
        if not last_message:
            return {"final_answer": "I couldn't understand your question. Please try again."}
        
        user_question = last_message.content if hasattr(last_message, 'content') else last_message.get('content', '')
        search_results = state.get("search_results", [])
        
        # Prepare context from search results
        context = ""
        if search_results:
            context = "\n\n".join([
                f"Source {i+1} ({r.get('query', 'Unknown')}):\n{r.get('result', 'No result')}"
                for i, r in enumerate(search_results[:3])
            ])
        
        if self.use_real_ai:
            # Use real AI to generate final answer
            system_prompt = """You are an AI research assistant. Provide a comprehensive, accurate answer to the user's question.
            
            Guidelines:
            1. Be specific and factual
            2. If search results are available, cite them as sources
            3. If you don't know something, say so clearly
            4. For technical topics (like Azure ML, cloud services), provide detailed, practical information
            5. Use bullet points and clear structure for better readability
            6. If the question is about recent developments, prioritize information from search results"""
            
            user_prompt = f"""User Question: {user_question}
            
            {'Search Results:' + context if context else 'No web search results available. Use your general knowledge to answer.'}
            
            Please provide a comprehensive answer:
            """
            
            try:
                response = await self.llm.ainvoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ])
                final_answer = response.content
                print(f"   ✅ Generated answer ({len(final_answer)} characters)")
                return {"final_answer": final_answer}
            except Exception as e:
                print(f"   ❌ Error generating answer: {str(e)}")
                return {"final_answer": f"Error generating response: {str(e)}\n\nPlease check your OpenAI API key and try again."}
        else:
            # Demo mode: provide helpful response about enabling real AI
            final_answer = self._get_demo_response(user_question)
            return {"final_answer": final_answer}
    
    def _get_demo_response(self, question: str) -> str:
        """Get demo response when real AI is not available"""
        
        # Check for specific topics
        question_lower = question.lower()
        
        if "azure ml" in question_lower or "azure machine learning" in question_lower:
            return """🔷 **About Azure Machine Learning (Azure ML)**

You asked about Azure ML, but I'm currently running in **DEMO MODE** without real AI capabilities.

**To get real, comprehensive answers about Azure ML:**

1. **Add your OpenAI API key** to `backend/.env`:"""

