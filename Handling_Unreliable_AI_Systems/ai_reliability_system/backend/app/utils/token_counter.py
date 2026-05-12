import tiktoken
from typing import List, Dict, Any

class TokenCounter:
    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self.encoder = tiktoken.encoding_for_model(model)
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in a string"""
        if not text:
            return 0
        return len(self.encoder.encode(text))
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of messages"""
        total = 0
        for message in messages:
            total += self.count_tokens(message.get('content', ''))
            total += self.count_tokens(message.get('role', ''))
        return total
    
    def estimate_cost(self, text: str) -> float:
        """Estimate cost for processing text"""
        tokens = self.count_tokens(text)
        rates = {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.001
        }
        rate = rates.get(self.model, 0.03)
        return (tokens / 1000) * rate
    
    def truncate_to_limit(self, text: str, limit: int = 4000) -> str:
        """Truncate text to fit within token limit"""
        tokens = self.encoder.encode(text)
        if len(tokens) <= limit:
            return text
        
        truncated_tokens = tokens[:limit]
        truncated_text = self.encoder.decode(truncated_tokens)
        
        # Add notice
        return truncated_text + "\n\n[Truncated due to length limits]"
    
    def get_token_distribution(self, text: str) -> Dict[str, Any]:
        """Get detailed token distribution"""
        tokens = self.encoder.encode(text)
        
        # Analyze token types (simplified)
        word_tokens = sum(1 for t in tokens if t > 200)  # Rough heuristic
        punctuation_tokens = sum(1 for t in tokens if t < 100)
        
        return {
            "total_tokens": len(tokens),
            "word_like_tokens": word_tokens,
            "punctuation_tokens": punctuation_tokens,
            "estimated_cost": self.estimate_cost(text)
        }