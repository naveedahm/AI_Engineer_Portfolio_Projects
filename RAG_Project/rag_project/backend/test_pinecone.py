# test_pinecone.py
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv

load_dotenv()

try:
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    print("✓ Pinecone initialized successfully (no deprecation warnings)")
    print(f"✓ Pinecone version: {pinecone.__version__}")
except Exception as e:
    print(f"Error: {e}")