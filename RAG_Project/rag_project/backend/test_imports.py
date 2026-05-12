# test_imports.py
print("Testing imports...")

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    print("✓ langchain_text_splitters")
except Exception as e:
    print(f"✗ langchain_text_splitters: {e}")

try:
    from langchain_core.documents import Document
    print("✓ langchain_core.documents")
except Exception as e:
    print(f"✗ langchain_core.documents: {e}")

try:
    from langchain_pinecone import PineconeVectorStore
    print("✓ langchain_pinecone")
except Exception as e:
    print(f"✗ langchain_pinecone: {e}")

try:
    from langchain_openai import OpenAIEmbeddings
    print("✓ langchain_openai")
except Exception as e:
    print(f"✗ langchain_openai: {e}")

print("All imports tested!")
