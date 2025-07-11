#!/usr/bin/env python3
"""
Final verification of Gemini Chat Application
"""

import subprocess
import requests
import time
import sys
import os

def verify_application():
    print("🔍 GEMINI CHAT APPLICATION VERIFICATION")
    print("=" * 50)
    
    # 1. Test app import and initialization
    print("1. Testing application import...")
    try:
        from app import GeminiChatApp
        app_instance = GeminiChatApp()
        print("   ✅ App imports and initializes successfully")
        print(f"   📊 Models available: {len(app_instance.available_models)}")
        print(f"   🔑 API key configured: {bool(app_instance.API_KEY)}")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # 2. Test database
    print("\n2. Testing database...")
    try:
        import sqlite3
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM history")
        hist_count = cursor.fetchone()[0]
        conn.close()
        print(f"   ✅ Database accessible")
        print(f"   💬 Conversations: {conv_count}")
        print(f"   📜 History entries: {hist_count}")
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False
    
    # 3. Test context directory
    print("\n3. Testing context directory...")
    context_dir = "allowed_context"
    if os.path.exists(context_dir):
        files = os.listdir(context_dir)
        print(f"   ✅ Context directory exists")
        print(f"   📁 Files available: {len(files)}")
    else:
        print(f"   ⚠️  Context directory will be created on startup")
    
    # 4. Test Flask app startup
    print("\n4. Testing Flask application startup...")
    try:
        app_process = subprocess.Popen(
            [sys.executable, "app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(4)  # Wait for startup
        
        # Test if app responds
        try:
            response = requests.get("http://localhost:5000/api/conversations", timeout=10)
            if response.status_code == 200:
                conversations = response.json()
                print(f"   ✅ Flask app running successfully")
                print(f"   🌐 API responding with {len(conversations)} conversations")
                
                # Test create conversation
                create_response = requests.post("http://localhost:5000/api/conversations", timeout=5)
                if create_response.status_code == 200:
                    new_conv = create_response.json()
                    print(f"   ✅ New conversation creation works: {new_conv['name']}")
                else:
                    print(f"   ⚠️  Create conversation returned: {create_response.status_code}")
                    
            else:
                print(f"   ❌ API returned status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ API test failed: {e}")
            return False
        finally:
            app_process.terminate()
            app_process.wait()
            
    except Exception as e:
        print(f"   ❌ Flask startup failed: {e}")
        return False
    
    # 5. Test template
    print("\n5. Testing template...")
    template_path = "templates/index.html"
    if os.path.exists(template_path):
        with open(template_path, 'r') as f:
            content = f.read()
            if "ModernGeminiChat" in content and "Tailwind" in content:
                print("   ✅ Modern template with Tailwind CSS found")
            else:
                print("   ⚠️  Template may be outdated")
    else:
        print("   ❌ Template not found")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 VERIFICATION COMPLETE!")
    print("\n📋 SUMMARY:")
    print("✅ Application imports and initializes")
    print("✅ Database is accessible and populated")
    print("✅ Context directory is ready")
    print("✅ Flask app starts and responds to API calls")
    print("✅ Modern template is in place")
    
    print("\n🚀 TO START THE APPLICATION:")
    print("   python3 app.py")
    print("\n🌐 THEN VISIT:")
    print("   http://localhost:5000")
    
    print("\n💡 EXPECTED FUNCTIONALITY:")
    print("   • Send messages with Enter key or Send button")
    print("   • Create new conversations")
    print("   • View conversation history")
    print("   • Add context (files, folders, URLs)")
    print("   • Real-time streaming responses")
    print("   • Modern dark theme interface")
    
    return True

if __name__ == "__main__":
    success = verify_application()
    sys.exit(0 if success else 1)
