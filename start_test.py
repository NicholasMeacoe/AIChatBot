#!/usr/bin/env python3
"""
Test startup script for the AIChatBot with upload functionality
"""

import os
import sys
from app import gemini_app

def main():
    print("🚀 Starting AIChatBot with Enhanced Upload Features")
    print("=" * 60)
    
    # Check if required directories exist
    if not os.path.exists('allowed_context'):
        print("📁 Creating allowed_context directory...")
        os.makedirs('allowed_context')
    
    print(f"📁 Context Directory: {os.path.abspath('allowed_context')}")
    print(f"🔑 API Key: {'✅ Set' if os.getenv('GOOGLE_API_KEY') else '❌ Missing'}")
    
    print("\n🌐 Starting server on http://localhost:5000")
    print("📋 Available endpoints:")
    print("  • GET  /                     - Main chat interface")
    print("  • POST /api/context/upload   - File upload endpoint")
    print("  • POST /api/context/check_images - Image detection")
    print("  • POST /api/chat             - Regular chat")
    print("  • POST /api/chat_multimodal  - Multimodal chat")
    
    print("\n🧪 Test the upload functionality:")
    print("  1. Open http://localhost:5000 in your browser")
    print("  2. Click 'Upload Files' in the context panel")
    print("  3. Drag and drop files or browse to select")
    print("  4. Click 'Upload' to test the functionality")
    
    print("\n🔧 For debugging, check the browser console (F12)")
    print("=" * 60)
    
    try:
        gemini_app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
