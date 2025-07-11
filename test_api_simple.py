#!/usr/bin/env python3
"""
Simple API test - run this while app.py is running
"""

import requests
import json

def test_endpoints():
    base_url = "http://localhost:5000"
    
    print("🧪 Testing API Endpoints")
    print("=" * 40)
    
    # Test main page
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Main page loads")
        else:
            print(f"❌ Main page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Main page error: {e}")
    
    # Test conversations API
    try:
        response = requests.get(f"{base_url}/api/conversations", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Conversations API: {len(data)} conversations")
        else:
            print(f"❌ Conversations API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Conversations API error: {e}")
    
    # Test create conversation
    try:
        response = requests.post(f"{base_url}/api/conversations", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Create conversation: {data.get('name', 'Unknown')}")
        else:
            print(f"❌ Create conversation failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Create conversation error: {e}")

if __name__ == "__main__":
    test_endpoints()
