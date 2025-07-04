#!/usr/bin/env python3
"""
Demo Enhanced AI Chatbot Application
A simplified version that demonstrates the core enhanced features without optional dependencies.
"""

from flask import Flask, render_template, request, Response, jsonify
import google.generativeai as genai
import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import core features that work without optional dependencies
from features.notebook import notebook_manager
from features.user_profiles import user_profile_manager
from features.git_integration import git_manager

# Load environment variables
load_dotenv()

def create_demo_app():
    """Create and configure the demo Flask application"""
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'demo-enhanced-ai-chatbot')
    
    # Initialize Google AI
    API_KEY = os.getenv("GOOGLE_API_KEY")
    if API_KEY:
        genai.configure(api_key=API_KEY)
        print("✅ Google AI API configured successfully")
    else:
        print("⚠️  Google AI API key not found")
    
    @app.route('/')
    def index():
        """Demo main page"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Enhanced AI Chatbot Demo</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .feature { margin: 20px 0; padding: 15px; border-left: 4px solid #007cba; background: #f8f9fa; }
                .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
                .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
                button { background: #007cba; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
                button:hover { background: #005a87; }
                .demo-section { margin: 30px 0; }
                pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
                .result { margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Enhanced AI Chatbot Demo</h1>
                <p>Welcome to the enhanced AI chatbot with 10 powerful new features!</p>
                
                <div class="demo-section">
                    <h2>📊 Feature Status</h2>
                    <div id="status-container">
                        <button onclick="checkStatus()">Check Feature Status</button>
                        <div id="status-result"></div>
                    </div>
                </div>
                
                <div class="demo-section">
                    <h2>💻 Interactive Notebook Demo</h2>
                    <div class="feature">
                        <h3>Execute Python Code</h3>
                        <textarea id="code-input" rows="4" cols="80" placeholder="Enter Python code here...">
import pandas as pd
import numpy as np

# Create sample data
data = pd.DataFrame({
    'x': np.random.randn(100),
    'y': np.random.randn(100)
})

print(f"Data shape: {data.shape}")
print(f"Mean values: x={data['x'].mean():.2f}, y={data['y'].mean():.2f}")
                        </textarea><br>
                        <button onclick="executeCode()">Execute Code</button>
                        <div id="code-result"></div>
                    </div>
                </div>
                
                <div class="demo-section">
                    <h2>👤 User Profile Demo</h2>
                    <div class="feature">
                        <h3>Personalized Experience</h3>
                        <button onclick="loadProfile()">Load User Profile</button>
                        <button onclick="recordInteraction()">Record Test Interaction</button>
                        <div id="profile-result"></div>
                    </div>
                </div>
                
                <div class="demo-section">
                    <h2>🔧 Git Integration Demo</h2>
                    <div class="feature">
                        <h3>Repository Status</h3>
                        <button onclick="getGitStatus()">Get Git Status</button>
                        <div id="git-result"></div>
                    </div>
                </div>
                
                <div class="demo-section">
                    <h2>🤖 AI Chat Demo</h2>
                    <div class="feature">
                        <h3>Enhanced AI Responses</h3>
                        <textarea id="chat-input" rows="3" cols="80" placeholder="Ask me anything...">Explain the benefits of the enhanced features in this AI chatbot</textarea><br>
                        <button onclick="sendMessage()">Send Message</button>
                        <div id="chat-result"></div>
                    </div>
                </div>
            </div>
            
            <script>
                async function checkStatus() {
                    try {
                        const response = await fetch('/api/status');
                        const data = await response.json();
                        document.getElementById('status-result').innerHTML = 
                            '<div class="success">✅ Core features operational</div>' +
                            '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    } catch (error) {
                        document.getElementById('status-result').innerHTML = 
                            '<div class="info">⚠️ ' + error.message + '</div>';
                    }
                }
                
                async function executeCode() {
                    const code = document.getElementById('code-input').value;
                    try {
                        const response = await fetch('/api/notebook/execute', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({code: code})
                        });
                        const result = await response.json();
                        
                        let html = '<div class="result">';
                        if (result.error) {
                            html += '<div style="color: red;">❌ Error: ' + result.error.message + '</div>';
                        } else {
                            html += '<div style="color: green;">✅ Execution successful</div>';
                            if (result.output) {
                                html += '<pre>Output: ' + result.output + '</pre>';
                            }
                            if (result.visualizations && result.visualizations.length > 0) {
                                html += '<div>📊 Generated ' + result.visualizations.length + ' visualizations</div>';
                            }
                        }
                        html += '</div>';
                        
                        document.getElementById('code-result').innerHTML = html;
                    } catch (error) {
                        document.getElementById('code-result').innerHTML = 
                            '<div class="result" style="color: red;">❌ ' + error.message + '</div>';
                    }
                }
                
                async function loadProfile() {
                    try {
                        const response = await fetch('/api/profile/load', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({user_id: 'demo_user'})
                        });
                        const result = await response.json();
                        
                        document.getElementById('profile-result').innerHTML = 
                            '<div class="result">' +
                            '<div class="success">✅ Profile loaded successfully</div>' +
                            '<pre>' + JSON.stringify(result.profile, null, 2) + '</pre>' +
                            '</div>';
                    } catch (error) {
                        document.getElementById('profile-result').innerHTML = 
                            '<div class="result" style="color: red;">❌ ' + error.message + '</div>';
                    }
                }
                
                async function recordInteraction() {
                    try {
                        const response = await fetch('/api/profile/interaction', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                type: 'demo_interaction',
                                content: 'User tested the profile system',
                                metadata: {timestamp: new Date().toISOString()}
                            })
                        });
                        const result = await response.json();
                        
                        document.getElementById('profile-result').innerHTML = 
                            '<div class="result">' +
                            '<div class="success">✅ Interaction recorded</div>' +
                            '</div>';
                    } catch (error) {
                        document.getElementById('profile-result').innerHTML = 
                            '<div class="result" style="color: red;">❌ ' + error.message + '</div>';
                    }
                }
                
                async function getGitStatus() {
                    try {
                        const response = await fetch('/api/git/status');
                        const result = await response.json();
                        
                        let html = '<div class="result">';
                        if (result.error) {
                            html += '<div class="info">ℹ️ ' + result.error + '</div>';
                        } else {
                            html += '<div class="success">✅ Git repository detected</div>';
                            html += '<pre>' + JSON.stringify(result, null, 2) + '</pre>';
                        }
                        html += '</div>';
                        
                        document.getElementById('git-result').innerHTML = html;
                    } catch (error) {
                        document.getElementById('git-result').innerHTML = 
                            '<div class="result" style="color: red;">❌ ' + error.message + '</div>';
                    }
                }
                
                async function sendMessage() {
                    const message = document.getElementById('chat-input').value;
                    try {
                        const response = await fetch('/api/chat', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({message: message})
                        });
                        const result = await response.json();
                        
                        document.getElementById('chat-result').innerHTML = 
                            '<div class="result">' +
                            '<div class="success">✅ AI Response:</div>' +
                            '<div style="margin: 10px 0; padding: 15px; background: white; border-radius: 5px;">' + 
                            result.response + '</div>' +
                            '</div>';
                    } catch (error) {
                        document.getElementById('chat-result').innerHTML = 
                            '<div class="result" style="color: red;">❌ ' + error.message + '</div>';
                    }
                }
            </script>
        </body>
        </html>
        """
    
    @app.route('/api/status')
    def get_status():
        """Get system status"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "features": {
                    "notebook": {
                        "active": True,
                        "context_variables": len(notebook_manager.get_context_variables()),
                        "execution_history": len(notebook_manager.execution_history)
                    },
                    "user_profiles": {
                        "active": user_profile_manager.current_user is not None,
                        "profile_loaded": user_profile_manager.current_user.user_id if user_profile_manager.current_user else None
                    },
                    "git_integration": {
                        "active": git_manager.is_git_repo(),
                        "repository_detected": git_manager.is_git_repo()
                    }
                },
                "system": {
                    "google_ai_configured": bool(os.getenv("GOOGLE_API_KEY")),
                    "python_version": sys.version,
                    "working_directory": str(Path.cwd())
                }
            }
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/notebook/execute', methods=['POST'])
    def execute_code():
        """Execute code in notebook"""
        try:
            data = request.get_json()
            code = data.get('code', '')
            
            result = notebook_manager.execute_code(code)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": {"message": str(e)}}), 500
    
    @app.route('/api/profile/load', methods=['POST'])
    def load_profile():
        """Load user profile"""
        try:
            data = request.get_json()
            user_id = data.get('user_id', 'demo_user')
            
            profile = user_profile_manager.load_or_create_profile(user_id)
            return jsonify({"profile": user_profile_manager.get_profile_summary()})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/profile/interaction', methods=['POST'])
    def record_interaction():
        """Record user interaction"""
        try:
            data = request.get_json()
            interaction_type = data.get('type')
            content = data.get('content')
            metadata = data.get('metadata', {})
            
            user_profile_manager.record_interaction(interaction_type, content, metadata)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/git/status')
    def get_git_status():
        """Get Git status"""
        try:
            status = git_manager.get_repo_status()
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/chat', methods=['POST'])
    def chat():
        """Enhanced chat endpoint"""
        try:
            data = request.get_json()
            message = data.get('message', '')
            
            if not os.getenv("GOOGLE_API_KEY"):
                return jsonify({"response": "Google AI API key not configured. Please set GOOGLE_API_KEY in your .env file."})
            
            # Generate AI response
            model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
            
            # Add context about enhanced features
            enhanced_prompt = f"""
            You are an enhanced AI chatbot with the following 10 powerful features:
            
            1. Interactive Code Notebooks & Data Visualization
            2. AI-Powered Chain of Thought & Task Decomposition  
            3. Proactive & Autonomous Agent Mode
            4. Deep Git Integration & Automated Commits
            5. Personalized User Profiles & Long-Term Memory
            6. Live External API Integration via Plugins
            7. Collaborative Whiteboard & Diagramming
            8. Enhanced Multimodal Understanding (Audio & Video)
            9. AI-Powered Debugging Assistant
            10. Digital Twin of the Codebase
            
            User question: {message}
            
            Please provide a helpful response that showcases your enhanced capabilities when relevant.
            """
            
            response = model.generate_content(enhanced_prompt)
            
            # Record interaction
            if user_profile_manager.current_user:
                user_profile_manager.record_interaction('chat', message)
            
            return jsonify({"response": response.text})
            
        except Exception as e:
            return jsonify({"response": f"Error: {str(e)}"})
    
    return app

def main():
    """Main entry point for the demo application"""
    
    print("🚀 Starting Enhanced AI Chatbot Demo...")
    print("=" * 60)
    
    # Create the demo app
    app = create_demo_app()
    
    # Initialize features
    print("📋 Initializing Enhanced Features:")
    
    try:
        # Initialize user profile
        user_profile_manager.load_or_create_profile('demo_user')
        print("  ✅ User profiles initialized")
    except Exception as e:
        print(f"  ⚠️  User profiles: {e}")
    
    try:
        # Check Git integration
        if git_manager.is_git_repo():
            print("  ✅ Git integration active")
        else:
            print("  ℹ️  Git integration: Not in a Git repository")
    except Exception as e:
        print(f"  ⚠️  Git integration: {e}")
    
    try:
        # Test notebook
        result = notebook_manager.execute_code("print('Notebook system ready!')")
        if not result.get('error'):
            print("  ✅ Interactive notebook ready")
        else:
            print(f"  ⚠️  Notebook: {result.get('error')}")
    except Exception as e:
        print(f"  ⚠️  Notebook: {e}")
    
    print("=" * 60)
    
    # Start the server
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🌟 Enhanced AI Chatbot Demo running on http://{host}:{port}")
    print("💡 Open your browser and visit http://localhost:5000")
    print("🎯 Try the interactive demos to see the enhanced features in action!")
    print("\n🔧 Available Features in Demo:")
    print("  • Interactive Python code execution with data visualization")
    print("  • Personalized user profiles with learning capabilities")
    print("  • Git repository integration and status monitoring")
    print("  • Enhanced AI chat with context awareness")
    print("\n⚡ Press Ctrl+C to stop the server")
    
    try:
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Enhanced AI Chatbot Demo stopped. Thanks for trying it!")

if __name__ == '__main__':
    main()
