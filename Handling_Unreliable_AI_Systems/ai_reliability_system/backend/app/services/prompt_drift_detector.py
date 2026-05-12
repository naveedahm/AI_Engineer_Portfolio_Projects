import numpy as np
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from collections import deque

class PromptDriftDetector:
    def __init__(self, baseline_prompt: str = None, window_size: int = 100):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.baseline_embedding = None
        if baseline_prompt:
            self.baseline_embedding = self.model.encode(baseline_prompt)
        self.prompt_history = deque(maxlen=window_size)
        self.drift_threshold = 0.15
        self.correction_attempts = {}  # Track fixes per prompt
        
    def detect_drift(self, current_prompt: str) -> bool:
        """Detect if current prompt has drifted from baseline"""
        if self.baseline_embedding is None:
            # Set as baseline if none exists
            self.baseline_embedding = self.model.encode(current_prompt)
            print(f"📝 Baseline prompt set: {current_prompt[:50]}...")
            return False
        
        current_embedding = self.model.encode(current_prompt)
        similarity = self.cosine_similarity(current_embedding, self.baseline_embedding)
        drift_score = 1 - similarity
        
        # Store in history
        self.prompt_history.append({
            "prompt": current_prompt,
            "drift_score": drift_score,
            "timestamp": time.time()
        })
        
        # Track drift for this prompt pattern
        prompt_hash = hash(current_prompt[:100])
        self.correction_attempts[prompt_hash] = self.correction_attempts.get(prompt_hash, 0) + 1
        
        is_drifted = drift_score > self.drift_threshold
        
        if is_drifted:
            self._log_drift_event(current_prompt, drift_score)
        
        return is_drifted

    def _log_drift_event(self, prompt: str, score: float):
        """Log drift events for monitoring"""
        log_entry = {
            "timestamp": time.time(),
            "prompt": prompt[:200],
            "drift_score": score,
            "threshold": self.drift_threshold
        }
        
        # Could log to file, Redis, or database
        print(f"📊 Prompt drift detected: {score:.3f} (threshold: {self.drift_threshold})")
        print(f"   Prompt: {prompt[:100]}...")
        
        # Store in Redis if available
        if hasattr(self, 'redis') and self.redis:
            self.redis.lpush("prompt_drift_log", json.dumps(log_entry))
    
    def fix_prompt(self, drifted_prompt: str) -> str:
        """Attempt to fix drifted prompt with multiple strategies"""
        
        # Strategy 1: Use most similar successful prompt from history
        best_prompt = self._find_best_template(drifted_prompt)
        
        if best_prompt:
            # Strategy 1 success: found similar prompt in history
            fixed = self._apply_template(best_prompt, drifted_prompt)
        else:
            # Strategy 2: Use baseline template
            fixed = self._apply_template("Please answer the following question concisely and accurately.", drifted_prompt)
        
        # Strategy 3: Remove common drift patterns
        fixed = self._remove_drift_patterns(fixed)
        
        # Add metadata about the fix
        prompt_hash = hash(drifted_prompt[:100])
        fix_count = self.correction_attempts.get(prompt_hash, 0)
        
        if fix_count > 3:
            # If same prompt keeps drifting, update baseline
            print(f"⚠️ Prompt consistently drifting, updating baseline")
            self.baseline_embedding = self.model.encode(drifted_prompt)
        
        return fixed
    
    def _find_best_template(self, drifted_prompt: str) -> Optional[str]:
        """Find the best template from history with low drift"""
        if not self.prompt_history:
            return None
        
        current_embedding = self.model.encode(drifted_prompt)
        best_template = None
        best_similarity = 0
        
        for record in self.prompt_history:
            if record["drift_score"] < 0.1:  # Low drift history
                template_embedding = self.model.encode(record["prompt"])
                similarity = self.cosine_similarity(current_embedding, template_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_template = record["prompt"]
        
        return best_template
    
    def _apply_template(self, template: str, user_query: str) -> str:
        """Apply template to user query"""
        # Extract the core question if template has a specific format
        if "?" in user_query or "what" in user_query.lower():
            return f"{template}\n\nUser Query: {user_query}\n\nPlease provide a clear and accurate response."
        else:
            return f"{template}\n\n{user_query}"
    
    def _remove_drift_patterns(self, text: str) -> str:
        """Remove common drift-inducing patterns"""
        # Remove excessive punctuation
        import re
        text = re.sub(r'[!?]{2,}', '?', text)
        
        # Remove casual language patterns that might cause drift
        casual_patterns = [
            "yo", "hey there", "sup", "what's up",
            "can you please", "would you mind", "could you possibly"
        ]
        
        for pattern in casual_patterns:
            text = text.replace(pattern, "")
        
        # Clean up extra spaces
        text = ' '.join(text.split())
        
        return text
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def get_drift_trend(self) -> float:
        """Get trend of prompt drift over time"""
        if len(self.prompt_history) < 10:
            return 0.0
        
        recent_scores = [record["drift_score"] for record in self.prompt_history]
        return np.mean(recent_scores[-10:]) - np.mean(recent_scores[:10])