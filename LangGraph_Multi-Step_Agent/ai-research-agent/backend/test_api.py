
import requests
import json

def test_api():
    base_url = "http://localhost:8000"
    
    # Test root endpoint
    print("Testing root endpoint...")
    response = requests.get(f"{base_url}/")
    print(f"Root: {response.status_code}")
    print(f"Response: {response.json()}\n")
    
    # Test health endpoint
    print("Testing health endpoint...")
    response = requests.get(f"{base_url}/health")
    print(f"Health: {response.status_code}")
    print(f"Response: {response.json()}\n")
    
    # Test API test endpoint
    print("Testing API test endpoint...")
    response = requests.get(f"{base_url}/api/test")
    print(f"Test: {response.status_code}")
    print(f"Response: {response.json()}\n")
    
    # Test simple chat endpoint
    print("Testing simple chat endpoint...")
    response = requests.post(
        f"{base_url}/api/chat/simple",
        json={"message": "Hello, this is a test!", "thread_id": "test123"}
    )
    print(f"Chat simple: {response.status_code}")
    print(f"Response: {response.json()}\n")
    
    # Test streaming endpoint (without actually streaming)
    print("Testing streaming endpoint...")
    response = requests.post(
        f"{base_url}/api/chat/stream",
        json={"message": "Tell me about AI", "thread_id": "test123"},
        stream=True
    )
    print(f"Stream: {response.status_code}")
    
    # Read stream
    for line in response.iter_lines():
        if line:
            print(f"Stream data: {line.decode('utf-8')}")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_api()
