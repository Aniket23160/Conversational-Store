#!/usr/bin/env python3
"""
Test script for the search API
"""
import requests
import json
import uuid

# Define test search queries
test_queries = [
    "serums",                      # Simple category search
    "something gentle for summer", # Vague seasonal request
    "moisturizer for dry skin",    # Specific with skin type
    "anti-aging products"          # Specific concern
]

# Create a session ID for testing
session_id = str(uuid.uuid4())

# Test each query
for query in test_queries:
    print(f"\n===== Testing query: '{query}' =====")
    
    # Create a test search request
    search_request = {
        "query": query,
        "session_id": session_id,
        "conversation_history": []
    }
    
    # Send the request to the API
    print("Sending search request...")
    response = requests.post(
        "http://localhost:8001/api/search",
        headers={"Content-Type": "application/json"},
        json=search_request
    )
    
    # Print the results
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print("Search successful!")
        print(f"Response type: {result.get('response_type')}")
        print(f"Message: {result.get('message')}")
        print(f"Products returned: {len(result.get('products', []))}")
        print(f"Follow-up question: {result.get('follow_up_question')}")
    else:
        print(f"Error: {response.text}")

