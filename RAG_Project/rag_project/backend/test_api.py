import requests
import json

# Test health endpoint
print("Testing health endpoint...")
try:
    response = requests.get("http://localhost:8000/health")
    print(f"Health check: {response.status_code} - {response.json()}")
except Exception as e:
    print(f"Health check failed: {e}")

# Test ask endpoint
print("\nTesting ask endpoint...")
test_question = "How do I reset my password?"
try:
    response = requests.post(
        "http://localhost:8000/ask",
        json={"question": test_question},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Answer: {data['answer'][:100]}...")
        print(f"Sources: {data['sources']}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")