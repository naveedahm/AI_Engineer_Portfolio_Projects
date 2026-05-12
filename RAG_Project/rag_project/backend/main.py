from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from rag_chain import get_answer
import uvicorn
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="RAG Support System", version="1.0")

# CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str

class Response(BaseModel):
    answer: str
    sources: List[str]

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/ask", response_model=Response)
async def ask(query: Query):
    try:
        logger.info(f"Question: {query.question[:50]}...")
        result = get_answer(query.question)
        return Response(answer=result["answer"], sources=result["sources"])
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)