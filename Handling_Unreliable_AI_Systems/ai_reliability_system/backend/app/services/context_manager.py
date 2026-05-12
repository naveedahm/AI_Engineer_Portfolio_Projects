import tiktoken
from typing import List, Dict, Any
from datetime import datetime

class ContextManager:
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.reserved_output_tokens = 1000
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.last_tokens_used = 0
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if not text:
            return 0
        return len(self.encoder.encode(text))
    
    def process(self, prompt: str, context: str = None) -> str:
        """Process prompt and context to fit within token limit"""
        if context:
            combined = f"{context}\n\n{prompt}"
        else:
            combined = prompt
        
        tokens = self.count_tokens(combined)
        self.last_tokens_used = tokens
        
        if tokens <= self.max_tokens - self.reserved_output_tokens:
            return combined
        
        # Need to truncate
        return self.truncate_text(combined)
    
    def truncate_text(self, text: str) -> str:
        """Truncate text to fit token limit"""
        tokens = self.encoder.encode(text)
        max_input_tokens = self.max_tokens - self.reserved_output_tokens
        
        if len(tokens) > max_input_tokens:
            truncated_tokens = tokens[:max_input_tokens]
            truncated_text = self.encoder.decode(truncated_tokens)
            
            # Add truncation notice
            truncated_text += "\n\n[Content truncated due to length limits]"
            return truncated_text
        
        return text
    
    def smart_chunk(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for processing"""
        tokens = self.encoder.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.encoder.decode(chunk_tokens)
            chunks.append(chunk_text)
        
        return chunks
    
    def calculate_cost(self, text: str, model: str = "gpt-4") -> float:
        """Calculate estimated cost for prompt"""
        token_count = self.count_tokens(text)
        rates = {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.001
        }
        return (token_count / 1000) * rates.get(model, 0.03)