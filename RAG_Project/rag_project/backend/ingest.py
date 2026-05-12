import os
import json
import re
import hashlib
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
import time

load_dotenv()

# ---------- Cleaning Functions ----------
def scrub_pii(text: str) -> str:
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC]', text)
    return text

def deduplicate(entries):
    seen = set()
    unique = []
    for e in entries:
        content = e["message"] + e["agent_response"]
        h = hashlib.md5(content.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(e)
    return unique

def clean_data(raw_data):
    cleaned = []
    for rec in raw_data:
        rec["message"] = scrub_pii(rec["message"])
        rec["agent_response"] = scrub_pii(rec["agent_response"])
        rec.pop("pii", None)
        if len(rec["message"]) < 5 or len(rec["agent_response"]) < 5:
            continue
        cleaned.append(rec)
    return deduplicate(cleaned)

# ---------- Ingestion ----------
def ingest_data(json_path="data/raw_chats.json"):
    # Load raw data
    with open(json_path, 'r') as f:
        raw_data = json.load(f)
    
    # Clean
    cleaned = clean_data(raw_data)
    print(f"Cleaned {len(cleaned)} records from {len(raw_data)}")
    
    # Create documents with proper structure
    documents = []
    for rec in cleaned:
        # IMPORTANT: Use page_content as the main text
        page_content = f"Question: {rec['message']}\nAnswer: {rec['agent_response']}"
        metadata = {
            "id": rec["id"], 
            "timestamp": rec["timestamp"],
            "source": rec.get("customer_id", "unknown")
        }
        documents.append(Document(page_content=page_content, metadata=metadata))
    
    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # Setup Pinecone
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index_name = "support-rag"
    
    # Delete existing index if needed
    if index_name in pc.list_indexes().names():
        print(f"Deleting existing index {index_name}...")
        pc.delete_index(index_name)
        time.sleep(10)  # Wait for deletion
    
    # Create new index
    print(f"Creating index {index_name}...")
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=os.environ.get("PINECONE_ENVIRONMENT", "us-east-1"))
    )
    time.sleep(5)  # Wait for index to be ready
    
    # Get the index
    index = pc.Index(index_name)
    
    # Create vector store and upsert
    vector_store = PineconeVectorStore(
        index=index,
        embedding=embeddings,
        text_key="text"
    )
    
    # Add documents
    vector_store.add_documents(chunks)
    print(f"Successfully ingested {len(chunks)} chunks into Pinecone")
    return vector_store

if __name__ == "__main__":
    # Adjust path as needed
    ingest_data("../data/raw_chats.json")