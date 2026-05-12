
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key found: {api_key[:20] if api_key else 'No'}...")

if api_key and api_key != "test-key-for-development":
    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API is working!'"}],
            max_tokens=20
        )
        print(f"✅ Success! Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ No valid API key found in .env file")

