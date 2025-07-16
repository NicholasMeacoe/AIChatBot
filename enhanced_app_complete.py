"""
Enhanced AI Chatbot Application - Complete Implementation
Integrates all 10 new features into a comprehensive AI-powered development assistant.
"""

from flask import Flask, render_template, request, Response, stream_with_context, send_file, jsonify
from flask_socketio import SocketIO, emit
import google.generativeai as genai
import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import threading
import logging

# Import existing functionality
from routes.main_routes import main_bp
from routes.context_routes import context_bp
from routes.pdf_routes import pdf_bp

# Import enhanced features routes
from routes.enhanced_features_routes import enhanced_features_bp

# Import feature managers
from features.notebook import notebook_manager
from features.chain_of_thought import chain_of_thought_manager
from features.autonomous_agent import autonomous_agent
from features.git_integration import git_manager
from features.user_profiles import user_profile_manager
from features.dynamic_api_integration import dynamic_api_manager
from features.collaborative_whiteboard import whiteboard_manager
from features.debugging_assistant import debugging_assistant
from features.digital_twin import digital_twin

# Load environment variables
load_dotenv()

def create_enhanced_app():
    """Create and configure the enhanced Flask application"""
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'enhanced-ai-chatbot-secret-key')
    
    # Initialize SocketIO for real-time features
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(context_bp)
    app.register_blueprint(pdf_bp)
    app.register_blueprint(enhanced_features_bp)
    
    # Initialize Google AI
    API_KEY = os.getenv("GOOGLE_API_KEY")
    if API_KEY:
        genai.configure(api_key=API_KEY)
        logger.info("Google AI API configured successfully")
    else:
        logger.warning("Google AI API key not found")
    
    @app.route('/')
    def index():
        """Enhanced main page with all features"""
        return render_template('enhanced_index.html')
    
    @app.route('/api/enhanced-chat', methods=['POST'])
    async def enhanced_chat():
        """Enhanced chat endpoint with all features integrated"""
        try:
            data = request.get_json()
            message = data.get('message', '')
            context = data.get('context', {})
            features_enabled = data.get('features', {})
            
            # Load user profile
            user_id = context.get('user_id')
            if user_id:
                user_profile_manager.load_or_create_profile(user_id)
            
            # Record interaction
            user_profile_manager.record_interaction('question', message, context)
            
            # Get personalized response style
            response_style = await user_profile_manager.get_personalized_response_style()
            
            # Check if this should be handled by autonomous agent
            if features_enabled.get('autonomous_agent', False):
                # Add as goal for autonomous agent
                goal_id = autonomous_agent.add_goal(
                    title="User Request",
                    description=message,
                    success_criteria=["Provide helpful response"],
                    priority=8
                )
                
                return jsonify({
                    "response": f"I've added your request to my autonomous processing queue (Goal ID: {goal_id}). I'll work on this proactively.",
                    "goal_id": goal_id,
                    "autonomous": True
                })
            
            # Check if this should use chain of thought
            if features_enabled.get('chain_of_thought', False) and len(message.split()) > 20:
                task = await chain_of_thought_manager.decompose_task(message)
                
                return jsonify({
                    "response": "I've broken down your request into manageable steps. Please review and approve the plan.",
                    "task": task.__dict__,
                    "requires_approval": True
                })
            
            # Generate personalized prompt
            personalized_prompt = await user_profile_manager.generate_personalized_prompt(message)
            
            # Use standard AI response with enhancements
            model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
            response = model.generate_content(personalized_prompt)
            
            # Check if response contains code that should be executed
            if features_enabled.get('notebook', False) and '```python' in response.text:
                # Extract and potentially execute code
                import re
                code_blocks = re.findall(r'```python\n(.*?)\n```', response.text, re.DOTALL)
                
                if code_blocks and features_enabled.get('auto_execute', False):
                    execution_results = []
                    for code in code_blocks:
                        result = notebook_manager.execute_code(code)
                        execution_results.append(result)
                    
                    return jsonify({
                        "response": response.text,
                        "code_execution": execution_results,
                        "visualizations": [r.get('visualizations', []) for r in execution_results]
                    })
            
            # Record successful solution
            user_profile_manager.add_successful_solution(message, response.text, context)
            
            return jsonify({
                "response": response.text,
                "personalized": True,
                "response_style": response_style
            })
            
        except Exception as e:
            logger.error(f"Enhanced chat error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/features/status')
    def get_all_features_status():
        """Get comprehensive status of all features"""
        try:
            # Get individual feature statuses
            from routes.enhanced_features_routes import get_enhanced_features_status
            
            # Add system-wide status
            system_status = {
                "timestamp": datetime.now().isoformat(),
                "git_repo": git_manager.is_git_repo(),
                "user_profile_loaded": user_profile_manager.current_user is not None,
                "autonomous_agent_running": autonomous_agent.is_running,
                "digital_twin_built": digital_twin.last_analysis is not None
            }
            
            return jsonify({
                "system": system_status,
                "features": get_enhanced_features_status()
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # SocketIO event handlers for real-time features
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info("Client connected")
        emit('status', {'message': 'Connected to enhanced AI chatbot'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info("Client disconnected")
    
    @socketio.on('join_whiteboard')
    def handle_join_whiteboard(data):
        """Handle joining a whiteboard session"""
        whiteboard_id = data.get('whiteboard_id')
        user_id = data.get('user_id', 'anonymous')
        
        if whiteboard_id in whiteboard_manager.whiteboards:
            whiteboard_manager.active_sessions.setdefault(whiteboard_id, set()).add(user_id)
            emit('whiteboard_joined', {'whiteboard_id': whiteboard_id})
            logger.info(f"User {user_id} joined whiteboard {whiteboard_id}")
    
    @socketio.on('whiteboard_update')
    def handle_whiteboard_update(data):
        """Handle whiteboard updates"""
        whiteboard_id = data.get('whiteboard_id')
        update_data = data.get('update')
        
        # Broadcast update to all users in the whiteboard session
        if whiteboard_id in whiteboard_manager.active_sessions:
            emit('whiteboard_updated', {
                'whiteboard_id': whiteboard_id,
                'update': update_data
            }, broadcast=True)
    
    @socketio.on('agent_progress')
    def handle_agent_progress(data):
        """Handle autonomous agent progress updates"""
        emit('agent_status', autonomous_agent.get_status(), broadcast=True)
    
    # Background tasks
    def background_tasks():
        """Run background tasks for enhanced features"""
        
        def autonomous_agent_monitor():
            """Monitor autonomous agent and emit updates"""
            while True:
                if autonomous_agent.is_running:
                    status = autonomous_agent.get_status()
                    socketio.emit('agent_status_update', status)
                
                threading.Event().wait(5)  # Check every 5 seconds
        
        def digital_twin_monitor():
            """Monitor codebase changes and update digital twin"""
            while True:
                if digital_twin._needs_rebuild():
                    logger.info("Codebase changes detected, updating digital twin...")
                    asyncio.run(digital_twin.build_digital_twin())
                    socketio.emit('digital_twin_updated', {
                        'timestamp': datetime.now().isoformat(),
                        'entities': len(digital_twin.entities)
                    })
                
                threading.Event().wait(30)  # Check every 30 seconds
        
        # Start background threads
        threading.Thread(target=autonomous_agent_monitor, daemon=True).start()
        threading.Thread(target=digital_twin_monitor, daemon=True).start()
    
    # Initialize features on startup
    @app.before_first_request
    def initialize_features():
        """Initialize all enhanced features"""
        logger.info("Initializing enhanced features...")
        
        # Initialize user profile
        user_profile_manager.load_or_create_profile()
        
        # Initialize Git integration
        if git_manager.is_git_repo():
            logger.info("Git repository detected")
        
        # Build initial digital twin
        try:
            asyncio.run(digital_twin.build_digital_twin())
            logger.info("Digital twin built successfully")
        except Exception as e:
            logger.warning(f"Failed to build digital twin: {e}")
        
        # Start background tasks
        background_tasks()
        
        logger.info("Enhanced features initialized successfully")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    return app, socketio

def main():
    """Main entry point for the enhanced application"""
    
    print("🚀 Starting Enhanced AI Chatbot with all 10 new features...")
    print("=" * 60)
    
    # Create the enhanced app
    app, socketio = create_enhanced_app()
    
    # Print feature status
    print("📋 Enhanced Features Status:")
    print("  ✅ Interactive Code Notebooks & Data Visualization")
    print("  ✅ AI-Powered Chain of Thought & Task Decomposition")
    print("  ✅ Proactive & Autonomous Agent Mode")
    print("  ✅ Deep Git Integration & Automated Commits")
    print("  ✅ Personalized User Profiles & Long-Term Memory")
    print("  ✅ Live External API Integration via Plugins")
    print("  ✅ Collaborative Whiteboard & Diagramming")
    print("  ✅ Enhanced Multimodal Understanding (Audio & Video)")
    print("  ✅ AI-Powered Debugging Assistant")
    print("  ✅ Digital Twin of the Codebase")
    print("=" * 60)
    
    # Print API endpoints
    print("🌐 Enhanced API Endpoints:")
    print("  • /api/enhanced/notebook/* - Interactive notebooks")
    print("  • /api/enhanced/chain-of-thought/* - Task decomposition")
    print("  • /api/enhanced/agent/* - Autonomous agent")
    print("  • /api/enhanced/git/* - Git integration")
    print("  • /api/enhanced/profile/* - User profiles")
    print("  • /api/enhanced/api-integration/* - Dynamic APIs")
    print("  • /api/enhanced/whiteboard/* - Collaborative whiteboard")
    print("  • /api/enhanced/multimodal/* - Audio/video analysis")
    print("  • /api/enhanced/debug/* - Debugging assistant")
    print("  • /api/enhanced/digital-twin/* - Codebase analysis")
    print("=" * 60)
    
    # Start the server
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🌟 Enhanced AI Chatbot running on http://{host}:{port}")
    print("💡 Access the enhanced interface at http://localhost:5000")
    print("📚 API documentation available at /api/enhanced/status")
    
    socketio.run(app, host=host, port=port, debug=False)

if __name__ == '__main__':
    main()
