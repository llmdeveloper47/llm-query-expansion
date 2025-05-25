# test_api.py
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    print("Health Check:", response.json())

def test_query_expansion(query):
    payload = {
        "query": query,
        "use_queue": False
    }
    response = requests.post(f"{BASE_URL}/expand", json=payload)
    result = response.json()
    print(f"Query: '{query}' -> '{result['expanded_query']}'")
    print(f"Processing time: {result['processing_time']:.3f}s")
    return result

# Test different queries
if __name__ == "__main__":
    print("Testing LLM Query Expansion API")
    print("=" * 40)
    
    # Health check
    test_health()
    print()
    
    # Test various queries
    test_queries = [
        "ML algos",
        "deep lerning",
        "AI/ML enginer",
        "computer vison",
        "data sci",
        "neural nets",
        "NLP techniques"
    ]
    
    for query in test_queries:
        test_query_expansion(query)
        print()