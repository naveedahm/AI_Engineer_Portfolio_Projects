from dotenv import load_dotenv
load_dotenv()

from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pinecone import Pinecone
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Pinecone
try:
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    logger.info("✓ Pinecone initialized")
except Exception as e:
    logger.error(f"✗ Pinecone initialization failed: {e}")
    raise

index_name = "support-rag"

# Check if index exists
if index_name not in pc.list_indexes().names():
    logger.error(f"Index '{index_name}' does not exist! Run ingest.py first.")
    raise Exception(f"Index '{index_name}' not found")

# Get the existing index
index = pc.Index(index_name)
logger.info(f"✓ Connected to index: {index_name}")

# Test index has vectors
stats = index.describe_index_stats()
if stats.total_vector_count == 0:
    logger.warning(f"Index '{index_name}' has no vectors! Run ingest.py to populate data.")
else:
    logger.info(f"✓ Index has {stats.total_vector_count} vectors")

# Create vector store
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = PineconeVectorStore(
    index=index,
    embedding=embeddings,
    text_key="text"
)

# FIXED: Configure retriever WITHOUT score_threshold
# Use only 'k' for number of results
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}  # Removed score_threshold
)

# Alternative: If you want threshold filtering, create a custom retriever
class ThresholdRetriever:
    """Custom retriever that filters by similarity score"""
    def __init__(self, vector_store, k=4, score_threshold=0.7):
        self.vector_store = vector_store
        self.k = k
        self.score_threshold = score_threshold
    
    def get_relevant_documents(self, query):
        # Get documents with scores
        docs_with_scores = self.vector_store.similarity_search_with_score(
            query, 
            k=self.k * 2  # Fetch more to filter
        )
        
        # Filter by threshold
        filtered_docs = [
            doc for doc, score in docs_with_scores 
            if score >= self.score_threshold
        ][:self.k]
        
        logger.info(f"Retrieved {len(filtered_docs)} documents (threshold: {self.score_threshold})")
        return filtered_docs
    
    async def aget_relevant_documents(self, query):
        return self.get_relevant_documents(query)

# Use either the simple retriever (no threshold) or the threshold retriever
# Option 1: Simple retriever (recommended for now)
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}
)

# Option 2: Threshold retriever (uncomment to use)
# retriever = ThresholdRetriever(vector_store, k=4, score_threshold=0.7)

# LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful support assistant. Use only the following context to answer. 
If you don't know the answer or the context doesn't contain relevant information, 
say 'I cannot find that information in my knowledge base.'

Context: {context}"""),
    ("user", "Question: {question}")
])

# QA chain with better error handling
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    chain_type_kwargs={"prompt": prompt},
    return_source_documents=True
)

def get_answer(question: str):
    """Get answer with detailed logging"""
    logger.info(f"Processing question: {question[:100]}...")
    
    if not question or len(question.strip()) == 0:
        return {"answer": "Please ask a valid question.", "sources": []}
    
    try:
        # Invoke the chain
        result = qa_chain.invoke({"query": question})
        
        # Log retrieval info
        num_sources = len(result.get("source_documents", []))
        logger.info(f"Retrieved {num_sources} source documents")
        
        # Check if we got any sources
        if num_sources == 0:
            logger.warning("No relevant documents found")
            return {
                "answer": "I couldn't find any relevant information in my knowledge base.",
                "sources": []
            }
        
        # Extract source IDs
        sources = []
        for doc in result["source_documents"]:
            # Try to get ID from metadata, or use first 50 chars of content as fallback
            source_id = doc.metadata.get("id", doc.page_content[:50] + "...")
            sources.append(source_id)
        
        return {
            "answer": result["result"],
            "sources": sources
        }
        
    except Exception as e:
        logger.error(f"Error in get_answer: {e}")
        raise