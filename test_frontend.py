#!/usr/bin/env python3
"""
Frontend Controls Verification Test
"""

import requests
import json

def test_frontend_controls():
    base_url = "http://localhost:5000"
    
    print("🎮 FRONTEND CONTROLS VERIFICATION")
    print("=" * 50)
    
    # Test 1: Main page loads with all controls
    print("1. Testing main page load...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Check for essential UI elements
            controls_to_check = [
                ("new-chat-btn", "New Chat Button"),
                ("conversations-list", "Conversations List"),
                ("model-select", "Model Selection Dropdown"),
                ("system-prompt", "System Prompt Textarea"),
                ("context-toggle", "Context Toggle Button"),
                ("message-input", "Message Input Field"),
                ("send-btn", "Send Button"),
                ("messages-container", "Messages Container"),
                ("file-modal", "File Selection Modal"),
                ("folder-modal", "Folder Selection Modal"),
                ("url-modal", "URL Input Modal")
            ]
            
            missing_controls = []
            for control_id, control_name in controls_to_check:
                if f'id="{control_id}"' in content:
                    print(f"   ✅ {control_name} found")
                else:
                    print(f"   ❌ {control_name} missing")
                    missing_controls.append(control_name)
            
            if not missing_controls:
                print("   ✅ All UI controls present in template")
            else:
                print(f"   ❌ Missing controls: {', '.join(missing_controls)}")
                
        else:
            print(f"   ❌ Page failed to load: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error loading page: {e}")
    
    # Test 2: JavaScript initialization
    print("\n2. Testing JavaScript components...")
    if 'ModernGeminiChat' in content:
        print("   ✅ ModernGeminiChat class found")
    else:
        print("   ❌ ModernGeminiChat class missing")
        
    if 'Tailwind' in content:
        print("   ✅ Tailwind CSS loaded")
    else:
        print("   ❌ Tailwind CSS missing")
        
    if 'marked' in content:
        print("   ✅ Markdown parser loaded")
    else:
        print("   ❌ Markdown parser missing")
    
    # Test 3: API endpoints that support frontend
    print("\n3. Testing supporting API endpoints...")
    
    endpoints_to_test = [
        ("/api/conversations", "GET", "Conversations List"),
        ("/api/conversations", "POST", "Create Conversation"),
        ("/api/context/files", "GET", "Context Files"),
        ("/api/context/folders", "GET", "Context Folders")
    ]
    
    for endpoint, method, description in endpoints_to_test:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
            elif method == "POST":
                response = requests.post(f"{base_url}{endpoint}", timeout=5)
                
            if response.status_code == 200:
                print(f"   ✅ {description} API working")
            else:
                print(f"   ❌ {description} API failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {description} API error: {e}")

if __name__ == "__main__":
    test_frontend_controls()
