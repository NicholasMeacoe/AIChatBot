from flask import Flask, render_template, request, Response, stream_with_context, send_file, jsonify
from werkzeug.utils import secure_filename
import google.generativeai as genai
import os
import re
import io
import img2pdf
import pytesseract
from PyPDF2 import PdfMerger
from PIL import Image
from io import BytesIO
import sqlite3
import json
from dotenv import load_dotenv
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import html
import base64
import uuid
from features.multimodal import MultiModalProcessor

# Load environment variables
load_dotenv()

class GeminiChatApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
        
        # Configuration
        self.API_KEY = os.getenv("GOOGLE_API_KEY")
        self.DEFAULT_MODEL = "gemini-2.5-flash"
        self.MAX_FILE_SIZE_MB = 10
        self.MAX_FILE_READ_BYTES = self.MAX_FILE_SIZE_MB * 1024 * 1024
        self.MAX_URL_CONTENT_BYTES = 2 * 1024 * 1024
        self.REQUEST_TIMEOUT = 10
        self.DB_NAME = 'chat_history.db'
        
        # Setup directories
        self.ALLOWED_CONTEXT_DIR = os.path.abspath("allowed_context")
        self.ensure_directories()
        
        # Initialize components
        self.multimodal_processor = MultiModalProcessor()
        self.setup_gemini()
        self.init_database()
        self.setup_routes()
        
    def ensure_directories(self):
        """Ensure required directories exist"""
        if not os.path.exists(self.ALLOWED_CONTEXT_DIR):
            try:
                os.makedirs(self.ALLOWED_CONTEXT_DIR)
                print(f"Created context directory: {self.ALLOWED_CONTEXT_DIR}")
            except OSError as e:
                print(f"Error creating context directory: {e}")
                
    def setup_gemini(self):
        """Initialize Gemini API and fetch available models"""
        self.available_models = [self.DEFAULT_MODEL]
        
        if not self.API_KEY:
            print("Warning: GOOGLE_API_KEY not found. Using default model only.")
            return
            
        try:
            genai.configure(api_key=self.API_KEY)
            self.available_models = self.fetch_available_models()
            print(f"Gemini configured. Available models: {len(self.available_models)}")
        except Exception as e:
            print(f"Error configuring Gemini: {e}")
            
    def fetch_available_models(self):
        """Fetch available models from Gemini API"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            models = []
            for model_info in data.get('models', []):
                if 'generateContent' in model_info.get('supportedGenerationMethods', []):
                    model_name = model_info.get('name', '')
                    if model_name.startswith('models/gemini'):
                        models.append(model_name.split('/')[-1])
                        
            return sorted(models) if models else [self.DEFAULT_MODEL]
        except Exception as e:
            print(f"Error fetching models: {e}")
            return [self.DEFAULT_MODEL]
            
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.DB_NAME)
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                system_prompt TEXT,
                model TEXT
            )
        ''')
        
        # Create history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                context_info TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        ''')
        
        # Create default conversation if none exist
        cursor.execute("SELECT COUNT(*) FROM conversations")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO conversations (name) VALUES (?)", ("Default Conversation",))
            
        conn.commit()
        conn.close()
        print(f"Database initialized: {os.path.abspath(self.DB_NAME)}")
        
    def get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
        
    def setup_routes(self):
        """Setup all Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html', 
                                 available_models=self.available_models,
                                 default_model=self.DEFAULT_MODEL)
        
        @self.app.route('/api/conversations/dates', methods=['GET'])
        def get_conversation_dates():
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT DATE(timestamp) as chat_date FROM conversations ORDER BY chat_date DESC")
            dates = [row['chat_date'] for row in cursor.fetchall()]
            conn.close()
            return jsonify(dates)

        @self.app.route('/api/conversations', methods=['GET'])
        def get_conversations():
            date_filter = request.args.get('date')
            conn = self.get_db()
            cursor = conn.cursor()
            if date_filter:
                try:
                    # Validate date format
                    datetime.strptime(date_filter, '%Y-%m-%d')
                    cursor.execute("SELECT * FROM conversations WHERE DATE(timestamp) = ? ORDER BY timestamp DESC", (date_filter,))
                except ValueError:
                    # Invalid date format, return all conversations
                    cursor.execute("SELECT * FROM conversations ORDER BY timestamp DESC")
            else:
                cursor.execute("SELECT * FROM conversations ORDER BY timestamp DESC")
            
            conversations = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify(conversations)
            
        @self.app.route('/api/conversations', methods=['POST'])
        def create_conversation():
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM conversations")
            count = cursor.fetchone()[0]
            name = f"Conversation {count + 1}"
            cursor.execute("INSERT INTO conversations (name) VALUES (?)", (name,))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return jsonify({'id': new_id, 'name': name})
            
        @self.app.route('/api/conversations/<int:conv_id>/history', methods=['GET'])
        def get_conversation_history(conv_id):
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_message, bot_response, timestamp 
                FROM history WHERE conversation_id = ? 
                ORDER BY timestamp ASC
            """, (conv_id,))
            history = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify(history)
            
        @self.app.route('/api/chat', methods=['POST'])
        def chat():
            return Response(
                stream_with_context(self.handle_chat_stream()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*'
                }
            )
            
        @self.app.route('/api/context/files', methods=['GET'])
        def list_context_files():
            return jsonify(self.get_context_files())
            
        @self.app.route('/api/context/folders', methods=['GET'])
        def list_context_folders():
            return jsonify(self.get_context_folders())
            
        @self.app.route('/api/conversations/<int:conv_id>/system_prompt', methods=['PUT'])
        def update_system_prompt(conv_id):
            try:
                data = request.json
                system_prompt = data.get('system_prompt', '')
                conn = self.get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE conversations SET system_prompt = ? WHERE id = ?", 
                             (system_prompt, conv_id))
                conn.commit()
                conn.close()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/api/conversations/<int:conv_id>/model', methods=['PUT'])
        def update_model(conv_id):
            try:
                data = request.json
                model = data.get('model', self.DEFAULT_MODEL)
                conn = self.get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE conversations SET model = ? WHERE id = ?", 
                             (model, conv_id))
                conn.commit()
                conn.close()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/context/upload', methods=['POST'])
        def upload_files():
            """Handle file uploads with drag-and-drop support"""
            if 'files' not in request.files:
                return jsonify({'error': 'No files provided'}), 400
            
            files = request.files.getlist('files')
            if not files or all(file.filename == '' for file in files):
                return jsonify({'error': 'No files selected'}), 400
            
            # Ensure upload directory exists
            if not self.ALLOWED_CONTEXT_DIR or not os.path.exists(self.ALLOWED_CONTEXT_DIR):
                return jsonify({'error': 'Upload directory not configured'}), 500
            
            # Configure allowed extensions
            ALLOWED_EXTENSIONS = {
                'txt', 'md', 'json', 'csv', 'pdf', 'doc', 'docx',
                'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
                'mp3', 'wav', 'm4a', 'ogg',
                'mp4', 'avi', 'mov', 'mkv'
            }
            
            def allowed_file(filename):
                return '.' in filename and \
                       filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
            
            uploaded_files = []
            errors = []
            
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    try:
                        # Create secure filename with timestamp to avoid conflicts
                        original_filename = secure_filename(file.filename)
                        name, ext = os.path.splitext(original_filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{name}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
                        
                        # Save file to allowed context directory
                        file_path = os.path.join(self.ALLOWED_CONTEXT_DIR, unique_filename)
                        file.save(file_path)
                        
                        uploaded_files.append(unique_filename)
                        
                    except Exception as e:
                        errors.append(f"Failed to upload {file.filename}: {str(e)}")
                else:
                    errors.append(f"File type not allowed: {file.filename}")
            
            response_data = {
                'uploaded_files': uploaded_files,
                'success_count': len(uploaded_files)
            }
            
            if errors:
                response_data['errors'] = errors
            
            if not uploaded_files:
                return jsonify({'error': 'No files were successfully uploaded', 'details': errors}), 400
            
            return jsonify(response_data)
        
        @self.app.route('/api/context/check_images', methods=['POST'])
        def check_images():
            """Check if context items contain image files"""
            data = request.json
            if not data or 'context_items' not in data:
                return jsonify({'has_images': False})
            
            context_items = data.get('context_items', [])
            if not isinstance(context_items, list):
                return jsonify({'has_images': False})
            
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            has_images = False
            image_files = []
            
            for item in context_items:
                if not item.startswith(('http://', 'https://')):
                    # Check file extension
                    ext = os.path.splitext(item.lower())[1]
                    if ext in image_extensions:
                        has_images = True
                        image_files.append(item)
            
            return jsonify({
                'has_images': has_images,
                'image_count': len(image_files),
                'image_files': image_files
            })
        
        @self.app.route('/api/multimedia/formats', methods=['GET'])
        def get_supported_formats():
            """Get supported multimedia formats"""
            try:
                formats = self.multimodal_processor.get_supported_formats()
                return jsonify({
                    'supported_formats': formats,
                    'total_formats': sum(len(formats[key]) for key in formats)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/multimedia/analyze', methods=['POST'])
        def analyze_multimedia_file():
            """Analyze a multimedia file and return metadata"""
            try:
                data = request.json
                file_path = data.get('file_path')
                
                if not file_path:
                    return jsonify({'error': 'Missing file_path parameter'}), 400
                
                # Ensure file is in allowed context directory
                abs_path = os.path.abspath(file_path)
                if not abs_path.startswith(self.ALLOWED_CONTEXT_DIR):
                    return jsonify({'error': 'File access denied'}), 403
                
                if not os.path.exists(abs_path):
                    return jsonify({'error': 'File not found'}), 404
                
                # Process the file
                result = self.multimodal_processor.process_file(abs_path)
                
                # Remove binary data from response for JSON serialization
                if result.get('type') == 'image' and 'data' in result:
                    result['data_size'] = len(result['data'])
                    del result['data']
                elif result.get('type') == 'video' and 'frames' in result:
                    for frame in result['frames']:
                        if 'data' in frame:
                            frame['data_size'] = len(frame['data'])
                            del frame['data']
                
                return jsonify(result)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/chat_multimodal', methods=['POST'])
        def chat_multimodal():
            """Handle multimodal chat with image support"""
            return Response(
                stream_with_context(self.handle_multimodal_chat_stream()),
                mimetype='text/event-stream',
                headers={'Cache-Control': 'no-cache'}
            )

    def handle_multimodal_chat_stream(self):
        """Handle streaming chat responses with enhanced multimodal data (images, audio, video)"""
        try:
            data = request.json
            user_message = data.get('message', '').strip()
            conversation_id = data.get('conversation_id')
            model_name = data.get('model', self.DEFAULT_MODEL)
            image_parts_b64 = data.get('image_parts', [])
            multimedia_files = data.get('multimedia_files', [])  # New: support for uploaded multimedia files

            if not user_message and not image_parts_b64 and not multimedia_files:
                yield f"data: {json.dumps({'error': 'Missing message or multimedia data'})}\n\n"
                return

            # Construct the prompt for the model
            prompt_parts = []
            if user_message:
                prompt_parts.append(user_message)

            # Process base64 images (existing functionality)
            for img_data in image_parts_b64:
                try:
                    image_bytes = base64.b64decode(img_data['data'])
                    pil_image = Image.open(BytesIO(image_bytes))
                    prompt_parts.append(pil_image)
                except Exception as e:
                    yield f"data: {json.dumps({'error': f'Failed to process image: {e}'})}\n\n"
                    return

            # Process multimedia files (new functionality)
            multimedia_context = []
            for file_info in multimedia_files:
                try:
                    file_path = file_info.get('path')
                    if file_path and os.path.exists(file_path):
                        # Ensure file is in allowed context directory
                        if not os.path.abspath(file_path).startswith(self.ALLOWED_CONTEXT_DIR):
                            yield f"data: {json.dumps({'error': f'File access denied: {file_path}'})}\n\n"
                            return
                        
                        file_type = self.multimodal_processor.detect_file_type(file_path)
                        
                        if file_type == 'image':
                            # Process image and add to prompt
                            processed_image = self.multimodal_processor._process_image(file_path)
                            if processed_image and processed_image.get('type') == 'image':
                                pil_image = Image.open(BytesIO(processed_image['data']))
                                prompt_parts.append(pil_image)
                                multimedia_context.append(f"Image: {os.path.basename(file_path)}")
                        
                        elif file_type == 'audio':
                            # Process audio and add transcription to prompt
                            audio_context = self.multimodal_processor.get_audio_context_for_gemini(file_path)
                            if audio_context:
                                audio_description = f"\n[AUDIO FILE: {os.path.basename(file_path)}]\n"
                                metadata = audio_context.get('metadata', {})
                                if metadata.get('duration') != 'Unknown':
                                    audio_description += f"Duration: {metadata.get('duration')}s\n"
                                
                                transcription = audio_context.get('transcription', '')
                                if transcription and not transcription.startswith('['):
                                    audio_description += f"Transcription: {transcription}\n"
                                else:
                                    audio_description += f"Transcription status: {transcription}\n"
                                
                                prompt_parts.append(audio_description)
                                multimedia_context.append(f"Audio: {os.path.basename(file_path)}")
                        
                        elif file_type == 'video':
                            # Process video and add frames to prompt
                            video_frames = self.multimodal_processor.get_video_frames_for_gemini(file_path)
                            if video_frames:
                                video_data = self.multimodal_processor._process_video(file_path)
                                metadata = video_data.get('metadata', {})
                                
                                video_description = f"\n[VIDEO FILE: {os.path.basename(file_path)}]\n"
                                video_description += f"Duration: {metadata.get('duration', 'Unknown')}s, "
                                video_description += f"Resolution: {metadata.get('resolution', 'Unknown')}\n"
                                video_description += f"Extracted {len(video_frames)} key frames:\n"
                                
                                prompt_parts.append(video_description)
                                
                                # Add the key frames
                                for i, frame_info in enumerate(video_frames):
                                    prompt_parts.append(f"Frame {i+1} (at {frame_info['timestamp']}s):")
                                    prompt_parts.append(frame_info['image'])
                                
                                multimedia_context.append(f"Video: {os.path.basename(file_path)} ({len(video_frames)} frames)")
                        
                except Exception as e:
                    yield f"data: {json.dumps({'error': f'Failed to process multimedia file: {e}'})}\n\n"
                    return

            # Generate response
            full_response = ""
            try:
                model = genai.GenerativeModel(model_name)
                response_stream = model.generate_content(prompt_parts, stream=True)
                
                for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"
                        
            except Exception as e:
                error_msg = f"Generation error: {str(e)}"
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return
                
            # Save to database
            try:
                conn = self.get_db()
                cursor = conn.cursor()
                
                # Create comprehensive context info
                context_info = []
                if image_parts_b64:
                    context_info.append(f"image_attachments: {len(image_parts_b64)}")
                if multimedia_context:
                    context_info.extend(multimedia_context)
                
                cursor.execute("""
                    INSERT INTO history (conversation_id, user_message, bot_response, context_info)
                    VALUES (?, ?, ?, ?)
                """, (conversation_id, user_message, full_response, json.dumps(context_info)))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Database save error: {e}")
                
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': f'Unexpected error: {str(e)}'})}\n\n"
            
    def handle_chat_stream(self):
        """Handle streaming chat responses"""
        try:
            data = request.json
            user_message = data.get('message', '').strip()
            conversation_id = data.get('conversation_id')
            model_name = data.get('model', self.DEFAULT_MODEL)
            context_items = data.get('context_items', [])
            
            if not user_message or not conversation_id:
                yield f"data: {json.dumps({'error': 'Missing message or conversation ID'})}\n\n"
                return
                
            # Process context
            full_context = ""
            context_errors = []
            
            for item in context_items:
                try:
                    if item.startswith(('http://', 'https://')):
                        context_part, error = self.process_url_context(item)
                    else:
                        context_part, error = self.process_file_context(item)
                        
                    if error:
                        context_errors.append(error)
                    if context_part:
                        full_context += context_part
                except Exception as e:
                    context_errors.append(f"Error processing {item}: {str(e)}")
                    
            # Send context errors if any
            if context_errors:
                yield f"data: {json.dumps({'context_errors': context_errors})}\n\n"
                
            # Generate response
            final_prompt = full_context + user_message
            full_response = ""
            
            try:
                model = genai.GenerativeModel(model_name)
                response_stream = model.generate_content(final_prompt, stream=True)
                
                for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"
                        
            except Exception as e:
                error_msg = f"Generation error: {str(e)}"
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return
                
            # Save to database
            try:
                conn = self.get_db()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO history (conversation_id, user_message, bot_response, context_info)
                    VALUES (?, ?, ?, ?)
                """, (conversation_id, user_message, full_response, json.dumps(context_items)))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Database save error: {e}")
                
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Unexpected error: {str(e)}'})}\n\n"
            
    def process_url_context(self, url):
        """Process URL context"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            if 'html' in response.headers.get('content-type', '').lower():
                soup = BeautifulSoup(response.content, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = ' '.join(soup.stripped_strings)
            else:
                text = response.text
                
            context = f"\n--- URL CONTENT: {url} ---\n{text[:self.MAX_URL_CONTENT_BYTES]}\n--- END URL CONTENT ---\n\n"
            return context, None
            
        except Exception as e:
            return "", f"Error fetching URL {url}: {str(e)}"
            
    def process_file_context(self, file_path):
        """Process file/folder context with enhanced multimodal support"""
        try:
            clean_path = file_path.strip().strip("'\"")
            
            # Security check
            if os.path.isabs(clean_path) or ".." in clean_path:
                return "", f"Invalid path: {file_path}"
                
            full_path = os.path.join(self.ALLOWED_CONTEXT_DIR, clean_path)
            
            if not os.path.exists(full_path):
                return "", f"Path not found: {file_path}"
                
            if os.path.isfile(full_path):
                file_size = os.path.getsize(full_path)
                if file_size > self.MAX_FILE_READ_BYTES:
                    return "", f"File too large: {file_path}"
                
                # Check if this is a multimedia file
                if self.multimodal_processor.is_multimedia_file(full_path):
                    file_type = self.multimodal_processor.detect_file_type(full_path)
                    
                    if file_type == 'image':
                        # For images, provide description and metadata
                        processed_image = self.multimodal_processor._process_image(full_path)
                        if processed_image and processed_image.get('type') == 'image':
                            metadata = processed_image.get('metadata', {})
                            context = f"\n--- IMAGE: {clean_path} ---\n"
                            context += f"Size: {metadata.get('original_size', 'Unknown')}\n"
                            context += f"Format: {metadata.get('format', 'Unknown')}\n"
                            context += f"File size: {metadata.get('file_size', 'Unknown')} bytes\n"
                            context += "--- END IMAGE ---\n\n"
                            return context, None
                    
                    elif file_type == 'audio':
                        # For audio, provide transcription and metadata
                        audio_context = self.multimodal_processor.get_audio_context_for_gemini(full_path)
                        if audio_context:
                            metadata = audio_context.get('metadata', {})
                            context = f"\n--- AUDIO: {clean_path} ---\n"
                            if metadata.get('duration') != 'Unknown':
                                context += f"Duration: {metadata.get('duration')}s\n"
                            if metadata.get('format'):
                                context += f"Format: {metadata.get('format')}\n"
                            
                            transcription = audio_context.get('transcription', '')
                            if transcription and not transcription.startswith('['):
                                context += f"Transcription: {transcription}\n"
                            else:
                                context += f"Transcription status: {transcription}\n"
                            context += "--- END AUDIO ---\n\n"
                            return context, None
                    
                    elif file_type == 'video':
                        # For video, provide metadata and frame information
                        video_data = self.multimodal_processor._process_video(full_path)
                        if video_data and video_data.get('type') == 'video':
                            metadata = video_data.get('metadata', {})
                            frames = video_data.get('frames', [])
                            
                            context = f"\n--- VIDEO: {clean_path} ---\n"
                            context += f"Duration: {metadata.get('duration', 'Unknown')}s\n"
                            context += f"Resolution: {metadata.get('resolution', 'Unknown')}\n"
                            context += f"FPS: {metadata.get('fps', 'Unknown')}\n"
                            context += f"Frame count: {metadata.get('frame_count', 'Unknown')}\n"
                            
                            if frames:
                                context += f"Extracted {len(frames)} key frames for analysis\n"
                                for i, frame in enumerate(frames):
                                    context += f"Frame {i+1}: timestamp {frame.get('timestamp', 0)}s\n"
                            
                            context += "--- END VIDEO ---\n\n"
                            return context, None
                
                # For regular text files, read content as before
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    context = f"\n--- FILE: {clean_path} ---\n{content}\n--- END FILE ---\n\n"
                    return context, None
                except UnicodeDecodeError:
                    # If it's not a text file and not multimedia, provide basic info
                    context = f"\n--- BINARY FILE: {clean_path} ---\n"
                    context += f"File size: {file_size} bytes\n"
                    context += "Binary file - content not displayed\n"
                    context += "--- END BINARY FILE ---\n\n"
                    return context, None
                
            elif os.path.isdir(full_path):
                items = os.listdir(full_path)
                listing = "\n".join(f"- {item}" for item in sorted(items)[:50])
                context = f"\n--- FOLDER: {clean_path} ---\n{listing}\n--- END FOLDER ---\n\n"
                return context, None
                
        except Exception as e:
            return "", f"Error processing {file_path}: {str(e)}"
            
        return "", f"Invalid path type: {file_path}"
        
    def get_context_files(self):
        """Get list of available context files"""
        files = []
        try:
            for root, dirs, filenames in os.walk(self.ALLOWED_CONTEXT_DIR):
                for filename in filenames:
                    rel_path = os.path.relpath(os.path.join(root, filename), self.ALLOWED_CONTEXT_DIR)
                    files.append(rel_path.replace(os.path.sep, '/'))
        except Exception as e:
            print(f"Error listing files: {e}")
        return sorted(files)
        
    def get_context_folders(self):
        """Get list of available context folders"""
        folders = []
        try:
            for root, dirnames, files in os.walk(self.ALLOWED_CONTEXT_DIR):
                for dirname in dirnames:
                    rel_path = os.path.relpath(os.path.join(root, dirname), self.ALLOWED_CONTEXT_DIR)
                    folders.append(rel_path.replace(os.path.sep, '/') + '/')
        except Exception as e:
            print(f"Error listing folders: {e}")
        return sorted(folders)
        
    def run(self, debug=True, host='0.0.0.0', port=5000):
        """Run the Flask application"""
        print("🚀 Starting Modern Gemini Chat Server...")
        print(f"📊 Database: {os.path.abspath(self.DB_NAME)}")
        print(f"📁 Context Directory: {self.ALLOWED_CONTEXT_DIR}")
        print(f"🤖 Available Models: {len(self.available_models)}")
        print(f"🌐 Server: http://{host}:{port}")
        print("=" * 50)
        
        self.app.run(debug=debug, host=host, port=port)

# Create global app instance
gemini_app = GeminiChatApp()
app = gemini_app.app  # For WSGI compatibility

if __name__ == '__main__':
    gemini_app.run()
