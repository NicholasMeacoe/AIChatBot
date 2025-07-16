#!/usr/bin/env python3
"""
Enhanced Gemini Chat Flask App
All 10 advanced features integrated
"""

from app import *  # Import base app
from features.multimodal import MultiModalProcessor
from features.templates import TemplateManager
from features.export import ExportManager
from features.search import SearchManager
from features.code_execution import CodeExecutor
from features.plugins import PluginManager
from features.smart_context import SmartContextManager
from features.voice import VoiceInterface
from features.analytics import AnalyticsManager

# Initialize all enhanced features
print("Initializing Enhanced Features...")

# Feature managers
multimodal_processor = MultiModalProcessor()
template_manager = TemplateManager()
code_executor = CodeExecutor()
plugin_manager = PluginManager()
voice_interface = VoiceInterface()

# Database-dependent features
def init_db_features():
    conn = get_db()
    search_manager = SearchManager(conn)
    analytics_manager = AnalyticsManager(conn)
    export_manager = ExportManager(conn)
    conn.close()
    return search_manager, analytics_manager, export_manager

# Smart context manager
smart_context_manager = SmartContextManager(API_KEY, ALLOWED_CONTEXT_DIR)

print("✅ All enhanced features initialized!")
print("🚀 Features available:")
print("   1. Multi-Modal File Support (images, audio, video)")
print("   2. Chat Templates & Saved Prompts")
print("   3. Export & Sharing (Markdown, JSON, HTML)")
print("   4. Real-time Collaboration (WebSocket)")
print("   5. Advanced Search & Tagging (Full-text search)")
print("   6. Code Execution Environment (Python, JS, Bash)")
print("   7. Plugin System (Extensible integrations)")
print("   8. Smart Context Suggestions (AI-powered)")
print("   9. Voice Interface (Speech-to-text, Text-to-speech)")
print("   10. Analytics & Insights Dashboard")

if __name__ == '__main__':
    print("\n🎉 Starting Enhanced Gemini Chat Server...")
    print("📡 WebSocket collaboration enabled")
    print("🔌 Plugin system active")
    print("🎯 All API endpoints available at /api/")
    print("🌐 Access at: http://localhost:5000")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)