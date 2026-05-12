
import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer

class HallucinationDetector:
    def __init__(self, ai_gateway=None):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.confidence_threshold = 0.7
        self.ai_gateway = ai_gateway  # Store reference for generating multiple responses
        
    async def check(self, prompt: str, response: str, use_consistency: bool = True) -> float:
        """Main entry point for hallucination detection"""
        
        # Basic heuristic checks
        heuristic_score = self._heuristic_check(prompt, response)
        
        # Self-consistency check (more accurate but slower)
        if use_consistency and self.ai_gateway:
            consistency_score = await self.self_consistency_check(prompt, response)
            # Combine both scores
            final_score = (heuristic_score + consistency_score) / 2
        else:
            final_score = heuristic_score
        
        return final_score
    
    def _heuristic_check(self, prompt: str, response: str) -> float:
        """Quick heuristic-based confidence check"""
        if len(response) < 10:
            return 0.3
        
        # Check for hedging language
        hedging_phrases = ["I think", "perhaps", "maybe", "might be", "possibly", "I believe"]
        hedging_count = sum(phrase in response.lower() for phrase in hedging_phrases)
        
        # Check for contradictions
        contradictions = self.detect_contradictions(response)
        
        confidence = 0.85
        if hedging_count > 2:
            confidence -= 0.1 * hedging_count
        if contradictions > 0:
            confidence -= 0.2 * contradictions
        
        return max(0.3, min(0.95, confidence))
    
    async def self_consistency_check(self, prompt: str, original_response: str, num_samples: int = 3) -> float:
        """
        Generate multiple responses and check consistency
        This helps detect hallucinations by seeing if the AI gives similar answers
        """
        if not self.ai_gateway:
            return 0.75  # Default if no gateway available
        
        try:
            from app.models.schemas import AIRequest
            
            # Generate multiple responses with slight temperature variation
            responses = [original_response]
            
            for i in range(num_samples - 1):
                # Create request with slightly higher temperature for variety
                consistency_request = AIRequest(
                    prompt=prompt,
                    temperature=0.8,  # Slightly higher for variation
                    max_retries=1
                )
                
                # Generate alternative response
                alt_result = await self.ai_gateway.process_request(consistency_request)
                responses.append(alt_result.output)
            
            # Calculate consistency between all responses
            consistency_score = self._calculate_consistency(responses)
            
            return consistency_score
            
        except Exception as e:
            print(f"⚠️ Self-consistency check failed: {e}")
            return 0.7  # Default on error
    
    def _calculate_consistency(self, responses: List[str]) -> float:
        """Calculate consistency score between multiple responses"""
        if len(responses) < 2:
            return 0.85
        
        # Encode all responses
        embeddings = self.model.encode(responses)
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                similarity = np.dot(embeddings[i], embeddings[j]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                )
                similarities.append(similarity)
        
        # Average similarity
        avg_similarity = np.mean(similarities)
        
        # Convert similarity to confidence
        # Higher similarity = more consistent = higher confidence
        consistency = avg_similarity
        
        return consistency
    
    def detect_contradictions(self, text: str) -> int:
        """Detect contradictions in text"""
        contradiction_pairs = [
            ("yes", "no"),
            ("true", "false"),
            ("always", "never"),
            ("all", "none"),
            ("increase", "decrease"),
            ("high", "low"),
            ("positive", "negative"),
            ("good", "bad")
        ]
        
        text_lower = text.lower()
        contradictions = 0
        
        for word1, word2 in contradiction_pairs:
            if word1 in text_lower and word2 in text_lower:
                # Check if both appear near each other
                pos1 = text_lower.find(word1)
                pos2 = text_lower.find(word2)
                if abs(pos1 - pos2) < 500:  # Within 500 characters
                    contradictions += 1
        
        return contradictions