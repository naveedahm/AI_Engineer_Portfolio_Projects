import asyncio
from app.services.prompt_drift_detector import PromptDriftDetector
from app.services.ai_gateway import AIGateway
import redis

async def test_prompt_fix():
    # Setup
    redis_client = redis.Redis(decode_responses=True)
    gateway = AIGateway(redis_client)
    
    # Test with drifted prompt
    drifted_prompts = [
        "yo bro tell me about AI like what's the deal with it?",
        "hey can you possibly maybe tell me something about machine learning please?",
        "What is!!!!!! neural networks?????? explain plz!!"
    ]
    
    for prompt in drifted_prompts:
        print(f"\n{'='*60}")
        print(f"Original: {prompt}")
        
        # Detect drift
        is_drifted = gateway.prompt_drift_detector.detect_drift(prompt)
        print(f"Drift detected: {is_drifted}")
        
        if is_drifted:
            # Fix the prompt
            fixed = gateway.prompt_drift_detector.fix_prompt(prompt)
            print(f"Fixed: {fixed}")
            
            # Process with fixed prompt
            from app.models.schemas import AIRequest
            request = AIRequest(prompt=fixed)
            response = await gateway.process_request(request)
            print(f"Response: {response.output[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_prompt_fix())