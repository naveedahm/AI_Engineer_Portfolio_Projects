import requests
import json

def test_endpoints():
    base_url = "http://localhost:8000"
    
    print("=" * 50)
    print("Testing Backend Endpoints")
    print("=" * 50)
    
    # Test 1: Root endpoint
    print("\n1. Testing Root endpoint...")
    response = requests.get(f"{base_url}/")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json().get('service', 'N/A')}")
    
    # Test 2: Health endpoint
    print("\n2. Testing Health endpoint...")
    response = requests.get(f"{base_url}/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    
    # Test 3: API Health endpoint
    print("\n3. Testing API Health endpoint...")
    response = requests.get(f"{base_url}/api/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    
    # Test 4: API Test endpoint
    print("\n4. Testing API Test endpoint...")
    response = requests.get(f"{base_url}/api/test")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Message: {data.get('message', 'N/A')}")
    
    # Test 5: Simple Chat endpoint
    print("\n5. Testing Simple Chat endpoint...")
    response = requests.post(
        f"{base_url}/api/chat/simple",
        json={"message": "Hello, test message!", "thread_id": "test123"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response preview: {data.get('message', '')[:100]}...")
    
    # Test 6: Main Chat endpoint
    print("\n6. Testing Main Chat endpoint...")
    response = requests.post(
        f"{base_url}/api/chat",
        json={"message": "Tell me about AI", "thread_id": "test123"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response preview: {data.get('message', '')[:100]}...")
    
    # Test 7: Streaming endpoint
    print("\n7. Testing Streaming endpoint...")
    response = requests.post(
        f"{base_url}/api/chat/stream",
        json={"message": "What is quantum computing?", "thread_id": "test123"},
        stream=True
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   Streaming data:")
        for i, line in enumerate(response.iter_lines()):
            if line and i < 5:  # Show first 5 events
                print(f"     {line.decode('utf-8')[:100]}")
        print("     ...")
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        test_endpoints()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to backend server.")
        print("   Make sure the backend is running: python run.py")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")