from flask import Flask, render_template, request, Response, stream_with_context, send_file, jsonify, redirect, url_for
from flask_socketio import SocketIO
from flask_login import LoginManager, login_required, current_user
import google.generativeai as genai
import os
import re
import io
import img2pdf
import pytesseract # Added for OCR
from PyPDF2 import PdfMerger # Added for merging PDFs
from PIL import Image # For image validation
from io import BytesIO # For handling byte streams
import sqlite3
import json
from dotenv import load_dotenv
from datetime import datetime
import markdown
from serpapi import GoogleSearch
import requests # For fetching URL content
from bs4 import BeautifulSoup # For parsing HTML
import html  # Add this import at the top with other imports

# Import OAuth2 components
from auth_config import AuthConfig
from oauth_auth import OAuth2Manager, login_required, admin_required, feature_required, rate_limit_check
from auth_routes import auth_bp
from user_management import UserManager

# Import enhanced features
try:
    from routes.enhanced_routes import enhanced_bp
    from features.collaboration import CollaborationManager
    from features.analytics import AnalyticsManager
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError:
    ENHANCED_FEATURES_AVAILABLE = False

# Load API Key
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
FETCHED_MODELS = [] # Global list to store fetched models

# --- Configuration ---
DEFAULT_MODEL_NAME = "gemini-2.5-pro-exp-03-25" # Fallback default
# Note: Free tier limits can change. These are examples based on typical free tiers.
# Users should verify current limits in their Google Cloud Console.
FREE_TIER_LIMITS = {
    "models/gemini-1.5-flash-latest": {"RPM": 60, "RPD": 1500, "TPM": 1_000_000},
    "models/gemini-1.0-pro": {"RPM": 60, "RPD": None, "TPM": None}, # Example: RPD/TPM might not be explicitly limited or documented
    "models/gemini-1.5-pro-latest": {"RPM": 2, "RPD": 50, "TPM": 1_000_000}, # Example limits if Pro is available in free tier
    # Add entries for other models as needed, key should match the API model name (e.g., "models/...")
}

MAX_FILE_SIZE_MB = 10  # Limit file size
MAX_FILE_READ_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
DB_NAME = 'chat_history.db'

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = AuthConfig.SECRET_KEY

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize OAuth2
oauth_manager = OAuth2Manager(app)
user_manager = UserManager()

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return user_manager.get_user(user_id)

# Register authentication blueprint
app.register_blueprint(auth_bp)

# Register enhanced features if available
if ENHANCED_FEATURES_AVAILABLE:
    app.register_blueprint(enhanced_bp)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Database Setup ---
def init_db():
    """Initialize the database with required tables"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                context_info TEXT,
                user_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()

# --- Gemini API Setup ---
def setup_gemini():
    """Setup Gemini API and fetch available models"""
    global FETCHED_MODELS
    
    if not API_KEY:
        print("⚠️  Warning: GOOGLE_API_KEY not found in environment variables.")
        print("   The app will use the default model without API validation.")
        return [DEFAULT_MODEL_NAME]
    
    try:
        genai.configure(api_key=API_KEY)
        models = genai.list_models()
        FETCHED_MODELS = [model.name for model in models if 'generateContent' in model.supported_generation_methods]
        
        if FETCHED_MODELS:
            print(f"✅ Successfully fetched {len(FETCHED_MODELS)} Gemini models:")
            for model in FETCHED_MODELS:
                limits = FREE_TIER_LIMITS.get(model, {})
                limit_info = f" (RPM: {limits.get('RPM', 'N/A')}, RPD: {limits.get('RPD', 'N/A')}, TPM: {limits.get('TPM', 'N/A')})" if limits else ""
                print(f"   - {model}{limit_info}")
            return FETCHED_MODELS
        else:
            print("⚠️  No compatible models found. Using default model.")
            return [DEFAULT_MODEL_NAME]
            
    except Exception as e:
        print(f"⚠️  Error fetching models: {e}")
        print("   Using default model as fallback.")
        return [DEFAULT_MODEL_NAME]

# --- Context Processing Functions ---
def is_safe_path(path, allowed_dir):
    """Check if the path is within the allowed directory"""
    try:
        allowed_path = os.path.realpath(allowed_dir)
        requested_path = os.path.realpath(os.path.join(allowed_dir, path))
        return requested_path.startswith(allowed_path)
    except:
        return False

def process_context_references(message, user_id=None):
    """Process @ references in the message and return processed message with context"""
    if not message:
        return message, []
    
    # Pattern to match @ references (with optional quotes)
    pattern = r'@\s*["\']?([^"\'@\s]+(?:\s+[^"\'@\s]+)*)["\']?'
    matches = re.findall(pattern, message)
    
    if not matches:
        return message, []
    
    context_parts = []
    context_info = []
    allowed_context_dir = os.path.join(os.getcwd(), 'allowed_context')
    
    # Ensure allowed_context directory exists
    os.makedirs(allowed_context_dir, exist_ok=True)
    
    for match in matches:
        path_or_url = match.strip()
        
        # Check if it's a URL
        if path_or_url.startswith(('http://', 'https://')):
            try:
                response = requests.get(path_or_url, timeout=10)
                response.raise_for_status()
                
                # Parse content based on content type
                content_type = response.headers.get('content-type', '').lower()
                if 'html' in content_type:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    content = soup.get_text()
                else:
                    content = response.text
                
                # Limit content size
                max_content_bytes = 50000  # 50KB limit
                if len(content.encode('utf-8')) > max_content_bytes:
                    content = content[:max_content_bytes//2] + "\n... [Content truncated due to size limit] ..."
                
                context_parts.append(f"Content from URL '{path_or_url}':\n{content}\n")
                context_info.append({
                    'type': 'url',
                    'path': path_or_url,
                    'size': len(content),
                    'status': 'success'
                })
                
            except Exception as e:
                error_msg = f"Error fetching URL '{path_or_url}': {str(e)}"
                context_parts.append(f"{error_msg}\n")
                context_info.append({
                    'type': 'url',
                    'path': path_or_url,
                    'error': str(e),
                    'status': 'error'
                })
        else:
            # Handle file/folder path
            if not is_safe_path(path_or_url, allowed_context_dir):
                error_msg = f"Access denied: Path '{path_or_url}' is outside allowed directory"
                context_parts.append(f"{error_msg}\n")
                context_info.append({
                    'type': 'file',
                    'path': path_or_url,
                    'error': error_msg,
                    'status': 'error'
                })
                continue
            
            full_path = os.path.join(allowed_context_dir, path_or_url)
            
            try:
                if os.path.isfile(full_path):
                    # Check file size
                    file_size = os.path.getsize(full_path)
                    if file_size > MAX_FILE_READ_BYTES:
                        error_msg = f"File '{path_or_url}' is too large ({file_size} bytes, max {MAX_FILE_READ_BYTES})"
                        context_parts.append(f"{error_msg}\n")
                        context_info.append({
                            'type': 'file',
                            'path': path_or_url,
                            'error': error_msg,
                            'status': 'error'
                        })
                        continue
                    
                    # Read file content
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    context_parts.append(f"Content of file '{path_or_url}':\n{content}\n")
                    context_info.append({
                        'type': 'file',
                        'path': path_or_url,
                        'size': file_size,
                        'status': 'success'
                    })
                    
                elif os.path.isdir(full_path):
                    # List directory contents
                    items = os.listdir(full_path)
                    items_list = '\n'.join(f"  - {item}" for item in sorted(items))
                    content = f"Contents of directory '{path_or_url}':\n{items_list}"
                    
                    context_parts.append(f"{content}\n")
                    context_info.append({
                        'type': 'directory',
                        'path': path_or_url,
                        'item_count': len(items),
                        'status': 'success'
                    })
                else:
                    error_msg = f"Path '{path_or_url}' not found"
                    context_parts.append(f"{error_msg}\n")
                    context_info.append({
                        'type': 'file',
                        'path': path_or_url,
                        'error': error_msg,
                        'status': 'error'
                    })
                    
            except Exception as e:
                error_msg = f"Error reading '{path_or_url}': {str(e)}"
                context_parts.append(f"{error_msg}\n")
                context_info.append({
                    'type': 'file',
                    'path': path_or_url,
                    'error': str(e),
                    'status': 'error'
                })
    
    # Combine context with original message
    if context_parts:
        context_text = '\n'.join(context_parts)
        processed_message = f"{context_text}\n---\n\nUser question: {message}"
    else:
        processed_message = message
    
    return processed_message, context_info

# --- Routes ---
@app.route('/')
@login_required
@feature_required('chat')
def index():
    """Main chat interface - requires authentication"""
    return render_template('index.html', 
                         models=FETCHED_MODELS or [DEFAULT_MODEL_NAME],
                         user=current_user)

@app.route('/chat', methods=['POST'])
@login_required
@feature_required('chat')
@rate_limit_check
def chat():
    """Handle chat requests - requires authentication and rate limiting"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        selected_model = data.get('model', DEFAULT_MODEL_NAME)
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Process context references
        processed_message, context_info = process_context_references(user_message, current_user.id)
        
        # Configure Gemini
        if API_KEY:
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel(selected_model)
            
            def generate():
                try:
                    response = model.generate_content(processed_message, stream=True)
                    full_response = ""
                    
                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            yield f"data: {json.dumps({'content': chunk.text})}\n\n"
                    
                    # Save to database with user association
                    save_to_database(user_message, full_response, context_info, current_user.id)
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    
                except Exception as e:
                    error_msg = f"Error generating response: {str(e)}"
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
            
            return Response(stream_with_context(generate()), 
                          mimetype='text/event-stream',
                          headers={'Cache-Control': 'no-cache'})
        else:
            return jsonify({'error': 'API key not configured'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
@login_required
@feature_required('history_view')
def get_history():
    """Get chat history for the current user"""
    try:
        date_filter = request.args.get('date')
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            if date_filter and date_filter != 'all':
                cursor.execute('''
                    SELECT timestamp, user_message, bot_response, context_info 
                    FROM history 
                    WHERE DATE(timestamp) = ? AND (user_id = ? OR user_id IS NULL)
                    ORDER BY timestamp DESC
                ''', (date_filter, current_user.id))
            else:
                cursor.execute('''
                    SELECT timestamp, user_message, bot_response, context_info 
                    FROM history 
                    WHERE user_id = ? OR user_id IS NULL
                    ORDER BY timestamp DESC
                ''', (current_user.id,))
            
            rows = cursor.fetchall()
            
            history = []
            for row in rows:
                context_info = json.loads(row[3]) if row[3] else []
                history.append({
                    'timestamp': row[0],
                    'user_message': row[1],
                    'bot_response': row[2],
                    'context_info': context_info
                })
            
            return jsonify(history)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history/dates')
@login_required
@feature_required('history_view')
def get_history_dates():
    """Get available history dates for the current user"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT DATE(timestamp) as date 
                FROM history 
                WHERE user_id = ? OR user_id IS NULL
                ORDER BY date DESC
            ''', (current_user.id,))
            
            dates = [row[0] for row in cursor.fetchall()]
            return jsonify(dates)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history/delete', methods=['POST'])
@login_required
@feature_required('history_delete')
def delete_history():
    """Delete history for a specific date - admin only"""
    try:
        data = request.get_json()
        date_to_delete = data.get('date')
        
        if not date_to_delete:
            return jsonify({'error': 'Date is required'}), 400
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Only allow users to delete their own history, admins can delete any
            if current_user.is_admin():
                cursor.execute('DELETE FROM history WHERE DATE(timestamp) = ?', (date_to_delete,))
            else:
                cursor.execute('DELETE FROM history WHERE DATE(timestamp) = ? AND user_id = ?', 
                             (date_to_delete, current_user.id))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': f'Deleted {deleted_count} entries for {date_to_delete}'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Keep all other existing routes (context, pdf conversion, etc.) with appropriate decorators...
# [Previous routes would be here with @login_required and @feature_required decorators added]

def save_to_database(user_message, bot_response, context_info, user_id):
    """Save chat interaction to database with user association"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO history (timestamp, user_message, bot_response, context_info, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                user_message,
                bot_response,
                json.dumps(context_info) if context_info else None,
                user_id
            ))
            conn.commit()
    except Exception as e:
        print(f"Error saving to database: {e}")

# --- Application Initialization ---
if __name__ == '__main__':
    print("🚀 Starting Gemini Chat Flask App with OAuth2 Authentication...")
    
    # Validate OAuth2 configuration
    try:
        AuthConfig.validate_config()
        print(f"✅ OAuth2 configured for {AuthConfig.OAUTH2_PROVIDER.title()}")
    except ValueError as e:
        print(f"❌ OAuth2 configuration error: {e}")
        print("   Please check your .env file and OAuth2 settings")
        exit(1)
    
    # Initialize databases
    init_db()
    print("✅ Chat history database initialized")
    
    # Setup Gemini API
    available_models = setup_gemini()
    
    # Create allowed_context directory
    allowed_context_dir = os.path.join(os.getcwd(), 'allowed_context')
    os.makedirs(allowed_context_dir, exist_ok=True)
    print(f"✅ Context directory: {allowed_context_dir}")
    
    print(f"✅ Server starting on http://0.0.0.0:5000/")
    print("📝 Access the application and log in to start chatting!")
    
    # Run the app
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
