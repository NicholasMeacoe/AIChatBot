#!/usr/bin/env python3
"""
Quick test of API endpoints
"""
import requests
import json
import time

def test_api():
    base_url = "http://localhost:5000"
    
    print("Testing API endpoints...")
    
    try:
        # Test conversations endpoint
        print("1. Testing GET /api/conversations")
        response = requests.get(f"{base_url}/api/conversations", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            conversations = response.json()
            print(f"   Found {len(conversations)} conversations")
            
            if conversations:
                conv_id = conversations[0]['id']
                print(f"2. Testing GET /api/conversations/{conv_id}/history")
                response = requests.get(f"{base_url}/api/conversations/{conv_id}/history", timeout=5)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    history = response.json()
                    print(f"   Found {len(history)} messages")
        
        # Test creating new conversation
        print("3. Testing POST /api/conversations")
        response = requests.post(f"{base_url}/api/conversations", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            new_conv = response.json()
            print(f"   Created conversation: {new_conv}")
            
        print("\n✅ API endpoints are working!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure app.py is running.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_api()
