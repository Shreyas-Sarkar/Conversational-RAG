import time
import requests
import os

BASE_URL = "http://localhost:8001"

def test_health():
    print("Testing /health...")
    resp = requests.get(f"{BASE_URL}/health")
    print(resp.status_code, resp.json())
    assert resp.status_code == 200

def test_demo_query():
    print("\nTesting demo query...")
    payload = {
        "chat_id": "compliance-handbook",
        "message": "What is SOC 2?",
        "top_k": 4,
        "similarity_threshold": 0.3
    }
    resp = requests.post(f"{BASE_URL}/query", json=payload, stream=True)
    print(resp.status_code)
    for line in resp.iter_lines():
        if line:
            print(line.decode('utf-8'))

if __name__ == "__main__":
    test_health()
    test_demo_query()
