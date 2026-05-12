from dotenv import load_dotenv
load_dotenv()

from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
import os

# Initialize
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = "support-rag"
index = pc.Index(index_name)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = PineconeVectorStore(index=index, embedding=embeddings, text_key="text")

# Test query
query = "How do I reset my password?"
results = vector_store.similarity_search(query, k=3)

print(f"Query: {query}")
print(f"Found {len(results)} results:\n")
for i, doc in enumerate(results, 1):
    print(f"{i}. {doc.page_content[:150]}...")
    print(f"   Metadata: {doc.metadata}\n")