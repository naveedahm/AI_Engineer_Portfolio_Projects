import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("RAG SYSTEM DIAGNOSTIC")
print("=" * 50)

# 1. Check Python version
print(f"\n1. Python version: {sys.version}")

# 2. Check environment variables
print("\n2. Environment variables:")
print(f"   OPENAI_API_KEY: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Missing'}")
print(f"   PINECONE_API_KEY: {'✓ Set' if os.getenv('PINECONE_API_KEY') else '✗ Missing'}")
print(f"   PINECONE_ENVIRONMENT: {os.getenv('PINECONE_ENVIRONMENT', 'Not set')}")

# 3. Test Pinecone
print("\n3. Testing Pinecone connection...")
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    print("   ✓ Pinecone initialized")
    
    indexes = pc.list_indexes().names()
    print(f"   Available indexes: {list(indexes)}")
    
    if "support-rag" in indexes:
        index = pc.Index("support-rag")
        stats = index.describe_index_stats()
        print(f"   ✓ Index 'support-rag' found")
        print(f"   Vector count: {stats.total_vector_count}")
        if stats.total_vector_count == 0:
            print("   ⚠ WARNING: Index has no vectors! Run ingest.py")
    else:
        print("   ✗ Index 'support-rag' not found! Run ingest.py")
        
except Exception as e:
    print(f"   ✗ Error: {e}")

# 4. Test OpenAI
print("\n4. Testing OpenAI connection...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # Test with a simple embedding
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input="test"
    )
    print("   ✓ OpenAI connection successful")
except Exception as e:
    print(f"   ✗ Error: {e}")

# 5. Test LangChain imports
print("\n5. Testing LangChain imports...")
try:
    from langchain_pinecone import PineconeVectorStore
    print("   ✓ langchain_pinecone")
    from langchain_openai import OpenAIEmbeddings
    print("   ✓ langchain_openai")
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    print("   ✓ langchain_text_splitters")
    print("   All imports successful")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 50)
print("DIAGNOSTIC COMPLETE")
print("=" * 50)