from flask import Flask, render_template, request, Response, stream_with_context, send_file, jsonify
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
import requests # For fetching URL content
from bs4 import BeautifulSoup # For parsing HTML
import html  # Add this import at the top with other imports

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

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            context_info TEXT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db() # Initialize DB on startup

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Return rows as dict-like objects
    return conn

def get_available_models(api_key):
    """Fetches available models from the Google Generative Language API."""
    if not api_key:
        print("Error: Cannot fetch models, API key is missing.")
        return [DEFAULT_MODEL_NAME] # Return default if no key

    models_list = []
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses
        data = response.json()

        # Filter for models that support 'generateContent' and are likely text models
        for model_info in data.get('models', []):
            # Check if 'generateContent' is a supported generation method
            supported_methods = model_info.get('supportedGenerationMethods', [])
            if 'generateContent' in supported_methods:
                 # Further filter based on name convention if desired (e.g., starts with 'models/gemini')
                 model_name = model_info.get('name')
                 if model_name and model_name.startswith('models/gemini'):
                    models_list.append(model_name.split('/')[-1]) # Extract just the model name (e.g., 'gemini-1.5-flash-latest')

        if not models_list:
             print("Warning: No suitable models found via API. Falling back to default.")
             return [DEFAULT_MODEL_NAME]
        print(f"Fetched available models: {models_list}")
        return sorted(models_list) # Return sorted list

    except requests.exceptions.RequestException as e:
        print(f"Error fetching models from API: {e}. Falling back to default.")
        return [DEFAULT_MODEL_NAME]
    except Exception as e:
        print(f"Unexpected error fetching models: {e}. Falling back to default.")
        return [DEFAULT_MODEL_NAME]

if not API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file. Using default model list.")
    FETCHED_MODELS = [DEFAULT_MODEL_NAME]
else:
    try:
        genai.configure(api_key=API_KEY)
        print("Gemini API Key configured.")
        FETCHED_MODELS = get_available_models(API_KEY)
        # Ensure default is in the list if fetching failed or didn't include it
        if DEFAULT_MODEL_NAME not in FETCHED_MODELS:
             FETCHED_MODELS.insert(0, DEFAULT_MODEL_NAME) # Add default at the beginning
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        FETCHED_MODELS = [DEFAULT_MODEL_NAME] # Fallback on config error

# (Keep process_context_path and parse_input_for_context functions as they are
#  in GeminiChatBot.py, just paste them here without the main() or load_api_key())

# Define the directory where context files are allowed
ALLOWED_CONTEXT_DIR_NAME = "allowed_context"
ALLOWED_CONTEXT_DIR = os.path.abspath(ALLOWED_CONTEXT_DIR_NAME)

# Ensure the allowed directory exists
if not os.path.exists(ALLOWED_CONTEXT_DIR):
    try:
        os.makedirs(ALLOWED_CONTEXT_DIR)
        print(f"Created allowed context directory: {ALLOWED_CONTEXT_DIR}")
    except OSError as e:
        print(f"Error creating allowed context directory '{ALLOWED_CONTEXT_DIR}': {e}")
        # Depending on the desired behavior, you might want to exit or handle this differently
        ALLOWED_CONTEXT_DIR = None # Indicate failure

# --- URL Fetching and Processing ---
MAX_URL_CONTENT_BYTES = 2 * 1024 * 1024 # Limit URL content size (e.g., 2MB)
REQUEST_TIMEOUT = 10 # Seconds

def fetch_and_process_url(url):
    """Fetches content from a URL, extracts text, and handles errors."""
    context_str = ""
    error_msg = None
    processed_url_info = {"original": url, "status": "error", "message": None}

    try:
        headers = { # Mimic a browser to avoid simple blocks
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        content_type = response.headers.get('content-type', '').lower()

        # Basic check for HTML/Text content
        if 'html' in content_type or 'text' in content_type:
            content = b""
            bytes_read = 0
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                bytes_read += len(chunk)
                if bytes_read > MAX_URL_CONTENT_BYTES:
                    error_msg = f"Error: URL content exceeds limit ({MAX_URL_CONTENT_BYTES / (1024*1024):.1f} MB). Truncated."
                    processed_url_info["message"] = error_msg
                    break # Stop reading

            # Decode content (attempt common encodings)
            try:
                decoded_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    decoded_content = content.decode('iso-8859-1')
                except UnicodeDecodeError:
                    decoded_content = content.decode('ascii', errors='ignore') # Fallback

            # Extract text using BeautifulSoup for HTML
            if 'html' in content_type:
                soup = BeautifulSoup(decoded_content, 'html.parser')
                # Remove script and style elements
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                # Get text, strip leading/trailing whitespace, join lines
                text = ' '.join(soup.stripped_strings)
            else: # Plain text
                text = decoded_content

            context_str += f"--- START CONTEXT FROM URL: {url} ---\n"
            context_str += text[:MAX_URL_CONTENT_BYTES] # Ensure final text doesn't exceed limit again
            if error_msg: # Append truncation warning if it occurred
                 context_str += "\n... (Content Truncated)"
            context_str += f"\n--- END CONTEXT FROM URL: {url} ---\n\n"
            processed_url_info["status"] = "ok"
            processed_url_info["context_added"] = True
            if error_msg: # Keep the truncation message
                 processed_url_info["message"] = error_msg

        else:
            error_msg = f"Error: Unsupported content type '{content_type}' for URL: {url}. Only HTML/Text supported."
            processed_url_info["message"] = error_msg

    except requests.exceptions.Timeout:
        error_msg = f"Error: Timeout fetching URL: {url} (>{REQUEST_TIMEOUT}s)"
        processed_url_info["message"] = error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching URL {url}: {e}"
        processed_url_info["message"] = error_msg
    except Exception as e:
        error_msg = f"Error processing URL {url}: {e}"
        processed_url_info["message"] = error_msg

    return context_str, error_msg, processed_url_info


def process_context_path(path):
    """
    Reads content from a file or lists contents of a folder within the ALLOWED_CONTEXT_DIR.
    Returns a formatted string with the context or an error message.
    """
    context_str = ""
    error_msg = None
    processed_path_info = {"original": path, "resolved": None, "status": "error", "message": None}

    if not ALLOWED_CONTEXT_DIR:
        error_msg = "Error: The allowed context directory is not configured or accessible."
        processed_path_info["message"] = error_msg
        return context_str, error_msg, processed_path_info

    clean_path = path.strip().strip("'\"") # Remove surrounding quotes and whitespace

    # Prevent absolute paths and path traversal attempts
    if os.path.isabs(clean_path) or ".." in clean_path.split(os.path.sep):
         error_msg = f"Error: Only relative paths within '{ALLOWED_CONTEXT_DIR_NAME}' are allowed. Path traversal ('..') or absolute paths are forbidden: '{path}'"
         processed_path_info["message"] = error_msg
         return context_str, error_msg, processed_path_info

    # Construct the full path securely within the allowed directory
    # os.path.join handles path separators correctly
    # os.path.abspath resolves the path, including removing redundant separators
    # os.path.realpath resolves any symbolic links (important on Linux/macOS)
    target_path = os.path.realpath(os.path.join(ALLOWED_CONTEXT_DIR, clean_path))
    processed_path_info["resolved"] = target_path # Store the actual path we are checking

    # Security Check: Ensure the resolved path is still within the allowed directory
    if not target_path.startswith(ALLOWED_CONTEXT_DIR + os.path.sep) and target_path != ALLOWED_CONTEXT_DIR:
        error_msg = f"Error: Access denied. Path '{path}' resolves outside the allowed directory '{ALLOWED_CONTEXT_DIR_NAME}'."
        processed_path_info["message"] = error_msg
        return context_str, error_msg, processed_path_info

    if not os.path.exists(target_path):
        error_msg = f"Error: Path not found within '{ALLOWED_CONTEXT_DIR_NAME}': '{clean_path}' (resolved to '{target_path}')"
        processed_path_info["message"] = error_msg
        return context_str, error_msg, processed_path_info

    try:
        relative_display_path = os.path.relpath(target_path, ALLOWED_CONTEXT_DIR) # Path relative to allowed dir for display

        if os.path.isfile(target_path):
            file_size = os.path.getsize(target_path)
            if file_size > MAX_FILE_READ_BYTES:
                 error_msg = (f"Error: File '{relative_display_path}' is too large "
                              f"({file_size / (1024*1024):.2f} MB > "
                              f"{MAX_FILE_SIZE_MB} MB limit). Skipping.")
                 processed_path_info["message"] = error_msg
                 return context_str, error_msg, processed_path_info

            context_str += f"--- START CONTEXT FROM FILE: {relative_display_path} ---\n"
            try:
                with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                    context_str += f.read()
            except Exception as e:
                 error_msg = f"Error reading file '{relative_display_path}': {e}"
                 processed_path_info["message"] = error_msg
                 return "", error_msg, processed_path_info # Return empty context on read error
            context_str += f"\n--- END CONTEXT FROM FILE: {relative_display_path} ---\n\n"
            processed_path_info["status"] = "ok"
            processed_path_info["context_added"] = True

        elif os.path.isdir(target_path):
            context_str += f"--- START CONTEXT FROM FOLDER CONTENTS: {relative_display_path}/ ---\n"
            try:
                items = os.listdir(target_path)
                folder_had_items = False
                if not items:
                    context_str += "(Folder is empty)\n"
                else:
                    folder_had_items = True
                    # Limit the number of files listed for performance/context size
                    MAX_FILES_IN_DIR = 50
                    count = 0
                    items.sort() # List items predictably
                    for item in items:
                        if count >= MAX_FILES_IN_DIR:
                            context_str += f"... (truncated listing at {MAX_FILES_IN_DIR} items)\n"
                            break

                        item_full_path = os.path.join(target_path, item)
                        # Ensure items listed are also within the allowed dir (redundant but safe)
                        if not os.path.realpath(item_full_path).startswith(ALLOWED_CONTEXT_DIR + os.path.sep):
                            context_str += f"--- SKIPPING ITEM (outside allowed dir): {item} ---\n"
                            continue

                        item_rel_path = os.path.join(relative_display_path, item)

                        if os.path.isfile(item_full_path):
                            try:
                                file_size = os.path.getsize(item_full_path)
                                if file_size > MAX_FILE_READ_BYTES:
                                    context_str += f"--- SKIPPING FILE (too large): {item_rel_path} ({file_size / (1024*1024):.2f} MB > {MAX_FILE_SIZE_MB} MB) ---\n"
                                else:
                                    # List file name and size
                                    context_str += f"- {item_rel_path} ({file_size / 1024:.1f} KB)\n"
                                    count += 1
                            except Exception as e:
                                context_str += f"--- ERROR ACCESSING FILE: {item_rel_path} ({e}) ---\n"
                        elif os.path.isdir(item_full_path):
                            context_str += f"- {item_rel_path}/ [DIR]\n"
                            count += 1
                        # else: ignore other types like symlinks etc.

            except Exception as e:
                 error_msg = f"Error processing directory '{relative_display_path}': {e}"
                 processed_path_info["message"] = error_msg
                 return "", error_msg, processed_path_info # Return empty context on error
            context_str += f"--- END CONTEXT FROM FOLDER CONTENTS: {relative_display_path}/ ---\n\n"
            processed_path_info["status"] = "ok"
            processed_path_info["context_added"] = folder_had_items # Context added if folder wasn't empty

        else:
            # This case should technically not be reached due to os.path.exists check earlier
            error_msg = f"Error: Path '{relative_display_path}' exists but is not a file or directory."
            processed_path_info["message"] = error_msg


    except Exception as e:
        error_msg = f"Error processing path '{path}': {e}"
        processed_path_info["message"] = error_msg


    # If context_str is empty but no error occurred (e.g., empty file/dir), set status ok
    if not error_msg and not context_str and processed_path_info["status"] != "ok":
         processed_path_info["status"] = "ok"
         processed_path_info["context_added"] = False
         processed_path_info["message"] = "Path found but contained no context (e.g., empty file or directory)."
         # Don't set error_msg here, let the calling function decide how to handle no context

    return context_str, error_msg, processed_path_info


def parse_input_for_context(user_input):
    """
    Finds @ {path} patterns, processes them using process_context_path,
    and returns the context string, the cleaned user message, errors,
    and detailed info about processed paths.
    """
    path_pattern = r'@\s*(?:"([^"]+)"|\'([^\']+)\'|(\S+))' # Same pattern
    matches = list(re.finditer(path_pattern, user_input))

    if not matches:
        return "", user_input, [], [] # No context found, return empty lists for errors/paths

    full_context = ""
    errors = []
    processed_paths_details = [] # Store detailed info from process_context_path
    processed_indices = set()

    for match in reversed(matches): # Process from end to start for easier index removal
        start, end = match.span()
        # Skip if this match overlaps with an already processed one (e.g., @ "path1 @ path2")
        if any(i in processed_indices for i in range(start, end)):
            continue

        # Extract path (quoted or unquoted)
        path = match.group(1) or match.group(2) or match.group(3)
        if path:
            # Call the updated context processing function
            context_part, error, path_info = process_context_path(path)

            # Store the detailed path processing info
            processed_paths_details.append(path_info)

            if error:
                # Add the specific error message from path processing
                errors.append(error)
            elif context_part:
                 # Prepend context only if successfully retrieved
                 full_context = context_part + full_context

            # Mark indices of the @{path} pattern as processed
            for i in range(start, end):
                processed_indices.add(i)

    # Build the cleaned message by excluding processed indices
    cleaned_message_list = [char for i, char in enumerate(user_input) if i not in processed_indices]
    cleaned_message = "".join(cleaned_message_list).strip()

    if not cleaned_message and full_context:
        cleaned_message = "(Referring to provided context)"
    elif not cleaned_message and not full_context and errors:
         cleaned_message = "(Error processing context, no message provided)"
    elif not cleaned_message and not full_context:
         cleaned_message = "(Empty message)"

    return full_context, cleaned_message, errors, processed_paths_details


# --- Flask Routes ---

@app.route('/')
def index():
    """Render the main chat page and load history, optionally filtered by date."""
    conn = get_db()
    cursor = conn.cursor()

    # Get distinct dates for the dropdown
    cursor.execute("SELECT DISTINCT DATE(timestamp) as chat_date FROM history ORDER BY chat_date DESC")
    available_dates = [row['chat_date'] for row in cursor.fetchall()]

    # Get selected date from query parameters
    selected_date = request.args.get('date')

    # Fetch and encode history
    if selected_date:
        try:
            datetime.strptime(selected_date, '%Y-%m-%d')
            cursor.execute(
                "SELECT user_message, bot_response, timestamp FROM history WHERE DATE(timestamp) = ? ORDER BY timestamp ASC",
                (selected_date,)
            )
        except ValueError:
            cursor.execute("SELECT user_message, bot_response, timestamp FROM history ORDER BY timestamp ASC")
            selected_date = None
    else:
        cursor.execute("SELECT user_message, bot_response, timestamp FROM history ORDER BY timestamp ASC")

    # HTML encode the history data
    history = [{
        'user_message': html.escape(row['user_message']),
        'bot_response': html.escape(row['bot_response']),
        'timestamp': row['timestamp']
    } for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template(
        'index.html',
        history=history,
        available_dates=available_dates,
        selected_date=selected_date,
        available_models=FETCHED_MODELS,
        default_model=DEFAULT_MODEL_NAME,
        usage_limits=FREE_TIER_LIMITS
    )

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Handle incoming chat messages and stream responses."""
    global FETCHED_MODELS  # Add this line
    if not API_KEY:
         return Response(json.dumps({"error": "Gemini API Key not configured."}), status=500, mimetype='application/json')

    data = request.json
    user_message = data.get('message')
    active_context_items = data.get('active_context', []) # Get active context list
    selected_model_name = data.get('model_name', DEFAULT_MODEL_NAME) # Get selected model or use default

    # Validate selected model against the fetched list
    if selected_model_name not in FETCHED_MODELS:
        # Attempt to refresh the list in case it changed since startup
        # Removed unnecessary global declaration
        print("Selected model not in known list, attempting to refresh...")
        FETCHED_MODELS = get_available_models(API_KEY)
        if selected_model_name not in FETCHED_MODELS:
             print(f"Error: Invalid model selected even after refresh: {selected_model_name}")
             return Response(json.dumps({"error": f"Invalid model selected: {selected_model_name}"}), status=400, mimetype='application/json')

    if not user_message:
        return Response(json.dumps({"error": "No message provided."}), status=400, mimetype='application/json')
    active_context_items = data.get('active_context', []) # Get active context list

    if not user_message:
        return Response(json.dumps({"error": "No message provided."}), status=400, mimetype='application/json')

    # --- Process Active Context Items ---
    full_context_str = ""
    context_errors = []
    processed_paths_info = [] # To store info for DB logging

    if active_context_items:
        print(f"Processing active context: {active_context_items}") # Debug log
        for item_path in active_context_items:
            if item_path.startswith('http://') or item_path.startswith('https://'):
                # Fetch and process URL content
                context_part, error, path_info = fetch_and_process_url(item_path)
                processed_paths_info.append(path_info) # Log URL processing attempt
                if error:
                    context_errors.append(error) # Collect errors
                if context_part:
                    full_context_str += context_part # Add successful context
            else:
                # Process file/folder paths
                context_part, error, path_info = process_context_path(item_path)
                processed_paths_info.append(path_info) # Log processing attempt
                if error:
                    context_errors.append(error) # Collect errors
                if context_part:
                    full_context_str += context_part # Add successful context

    # --- Construct Final Prompt ---
    # Prepend the gathered context to the user's message
    final_prompt = full_context_str + user_message

    # Store original user message and context info for DB
    original_user_message_for_db = user_message # Keep original message separate
    context_info_json = json.dumps(processed_paths_info) if processed_paths_info else None

    # Basic check: Ensure there's something to send to the model
    if not final_prompt.strip() and not context_errors:
         return Response(json.dumps({"error": "Cannot send an empty message."}), status=400, mimetype='application/json')

    # --- Streaming Response ---
    def generate_response():
        full_bot_response = ""
        try:
            # Start a new chat session for each request OR manage sessions if needed
            # For simplicity, starting fresh each time. For history continuity with Gemini,
            # you'd need session management (e.g., using Flask sessions or a cache).
            # Let's assume the Gemini library handles history internally for a `chat` object
            # If not, we need to pass history manually. The current GeminiChatBot.py starts fresh.
            # Let's stick to the simpler approach first: stateless requests.
            # Instantiate the model based on user selection for this request
            try:
                current_model = genai.GenerativeModel(selected_model_name)
                print(f"Using model: {selected_model_name} for chat request.") # Log model usage
            except Exception as e:
                 print(f"Error instantiating model '{selected_model_name}': {e}")
                 yield f"data: {json.dumps({'error': f'Failed to load model {selected_model_name}: {e}'})}\n\n"
                 return # Stop generation

            # To enable streaming: use stream=True
            stream = current_model.generate_content(final_prompt, stream=True)

            # Send context errors first, if any
            if context_errors:
                error_data = json.dumps({"context_error": "\n".join(context_errors)})
                yield f"data: {error_data}\n\n"

            for chunk in stream:
                if chunk.text:
                    full_bot_response += chunk.text
                    # Send chunk to client via SSE
                    data = json.dumps({"text": chunk.text})
                    yield f"data: {data}\n\n" # SSE format: data: <json_string>\n\n

            # --- Save to Database ---
            # Save after the full response is generated
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (user_message, bot_response, context_info) VALUES (?, ?, ?)",
                (original_user_message_for_db, full_bot_response, context_info_json) # Store original message + context info
            )
            conn.commit()
            conn.close()
            print(f"Saved interaction: User: '{user_message[:50]}...', Bot: '{full_bot_response[:50]}...'")

            # Signal end of stream (optional, depends on client handling)
            yield f"data: {json.dumps({'end_stream': True})}\n\n"

        except Exception as e:
            print(f"Error during Gemini generation or DB save: {e}")
            # Send error to client via SSE
            error_data = json.dumps({"error": f"An error occurred: {e}"})
            yield f"data: {error_data}\n\n"
            # Also save the error state? Maybe not, depends on requirements.

    # Use stream_with_context for generators that access request context
    return Response(stream_with_context(generate_response()), mimetype='text/event-stream')


# --- Image to PDF Conversion Route ---
@app.route('/convert', methods=['POST'])
def convert_images_to_pdf():
    """Handles multiple image uploads and converts them to a single PDF, optionally with OCR."""
    if 'images' not in request.files:
        return jsonify({"error": "No image files provided"}), 400

    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No selected files"}), 400

    # Check if OCR is requested (convert string 'true'/'false' to boolean)
    ocr_enabled = request.form.get('ocr_enabled', 'false').lower() == 'true'

    processed_files = [] # Store validated image data (bytes or PIL Image objects)
    allowed_extensions = {'jpeg', 'jpg'}

    for file in files:
        # Basic filename check
        if '.' not in file.filename or \
           file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({"error": f"Invalid file type: {file.filename}. Only JPEG/JPG allowed."}), 400

        try:
            img_bytes = file.read()
            # Validate image format using Pillow
            img = Image.open(BytesIO(img_bytes))
            if img.format.lower() not in ['jpeg']:
                return jsonify({"error": f"Invalid image format detected in file: {file.filename}. Only JPEG/JPG allowed."}), 400
            img.verify() # Verify image integrity (re-open after verify)
            img = Image.open(BytesIO(img_bytes)) # Re-open image after verification

            # Store either bytes (for img2pdf) or PIL image (for pytesseract)
            processed_files.append(img if ocr_enabled else img_bytes)

        except Exception as e:
            print(f"Error processing file {file.filename}: {e}")
            return jsonify({"error": f"Invalid or corrupted image file: {file.filename}. Error: {e}"}), 400

    if not processed_files:
        return jsonify({"error": "No valid JPEG images found to convert"}), 400

    try:
        output_pdf_stream = BytesIO()

        if ocr_enabled:
            # --- OCR Path ---
            merger = PdfMerger()
            try:
                for i, img in enumerate(processed_files):
                    # Create searchable PDF for each image in memory
                    pdf_data = pytesseract.image_to_pdf_or_hocr(img, extension='pdf')
                    pdf_stream = BytesIO(pdf_data)
                    merger.append(pdf_stream)
                    print(f"Processed image {i+1} with OCR.")
                # Write the merged PDF to the output stream
                merger.write(output_pdf_stream)
                merger.close()
            except pytesseract.TesseractNotFoundError:
                 print("TesseractNotFoundError: Tesseract is not installed or not in your PATH.")
                 return jsonify({"error": "OCR Error: Tesseract is not installed or not found. Please install Tesseract and ensure it's in your system's PATH."}), 500
            except Exception as ocr_error:
                 print(f"Error during OCR processing: {ocr_error}")
                 return jsonify({"error": f"An error occurred during OCR processing: {ocr_error}"}), 500
        else:
            # --- Non-OCR Path (using img2pdf) ---
            pdf_bytes = img2pdf.convert(processed_files) # processed_files contains bytes here
            output_pdf_stream = BytesIO(pdf_bytes)

        # Reset stream position before sending
        output_pdf_stream.seek(0)

        # Send the final PDF file back to the client
        return send_file(
            output_pdf_stream,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='converted_images.pdf'
        )

    except Exception as e:
        print(f"Error during PDF generation/sending: {e}")
        return jsonify({"error": f"PDF generation failed: {e}"}), 500

# --- Delete History Route ---
@app.route('/summarize_context', methods=['POST'])
def summarize_context():
    """Summarize a list of provided context items (files/folders/URLs)."""
    data = request.json
    if not data or 'context_items' not in data:
        return jsonify({"error": "No context items provided"}), 400

    context_items = data['context_items']
    if not context_items:
        return jsonify({"error": "Empty context items list"}), 400

    # Process each context item and gather their content
    full_context = ""
    errors = []
    processed_paths_info_summary = [] # Separate tracking for summary context

    for item in context_items:
        if item.startswith('http://') or item.startswith('https://'):
            # Fetch and process URL content
            context_part, error, path_info = fetch_and_process_url(item)
            processed_paths_info_summary.append(path_info)
            if error:
                errors.append(error) # Collect errors
            if context_part:
                full_context += context_part # Add successful context
        else:
            # For files/folders, use our existing context processing
            context_part, error, path_info = process_context_path(item)
            processed_paths_info_summary.append(path_info)
            if error:
                errors.append(error)
            if context_part:
                full_context += context_part

    if not full_context:
        if errors:
            return jsonify({"error": "Failed to process context items", "details": errors}), 400
        return jsonify({"error": "No content found in provided context items"}), 400

    # Get selected model from request or use default (passed in data for consistency)
    selected_model_name = data.get('model_name', DEFAULT_MODEL_NAME)
    if selected_model_name not in FETCHED_MODELS:
         # Don't refresh here, just return error if invalid model was sent
         return jsonify({"error": f"Invalid model selected for summary: {selected_model_name}"}), 400

    try:
        # Instantiate the selected model
        print(f"Using model: {selected_model_name} for summary request.") # Log model usage
        current_model = genai.GenerativeModel(selected_model_name)

        # Create a prompt that asks for a summary
        prompt = f"""Please provide a concise summary of the following context:
        
{full_context}

Focus on:
1. Main topics or themes
2. Key files/components and their relationships
3. Important code structures or patterns
4. Any notable features or configurations

Keep the summary clear and well-organized."""

        response = genai.model.generate_content(prompt)
        summary = response.text

        if errors:
            # Include any non-fatal errors in the response
            return jsonify({
                "summary": summary,
                "warnings": errors
            })
        return jsonify({"summary": summary})

    except Exception as e:
        print(f"Error generating context summary: {e}")
        return jsonify({"error": f"Failed to generate summary: {str(e)}"}), 500

@app.route('/fetch_history', methods=['GET'])
def fetch_history():
    """Fetch chat history for a specific date or all history."""
    selected_date = request.args.get('date')
    conn = get_db()
    cursor = conn.cursor()

    try:
        if selected_date:
            # Validate date format
            datetime.strptime(selected_date, '%Y-%m-%d')
            cursor.execute(
                "SELECT user_message, bot_response, timestamp FROM history WHERE DATE(timestamp) = ? ORDER BY timestamp ASC",
                (selected_date,)
            )
        else:
            cursor.execute("SELECT user_message, bot_response, timestamp FROM history ORDER BY timestamp ASC")

        history = cursor.fetchall()
        history_list = []
        
        for row in history:
            # HTML encode both user message and bot response
            history_list.append({
                'user_message': html.escape(row['user_message']),
                'bot_response': html.escape(row['bot_response']),
                'timestamp': row['timestamp']
            })
        
        return jsonify({'history': history_list})
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/delete_history/<string:date_str>', methods=['DELETE'])
def delete_history(date_str):
    """Delete chat history for a specific date."""
    try:
        # Validate date format
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    conn = None # Initialize conn to None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE DATE(timestamp) = ?", (date_str,))
        conn.commit()
        deleted_count = cursor.rowcount # Get the number of deleted rows
        print(f"Deleted {deleted_count} entries for date: {date_str}")
        return jsonify({"success": True, "message": f"Deleted history for {date_str}.", "deleted_count": deleted_count}), 200
    except sqlite3.Error as e:
        print(f"Database error deleting history for {date_str}: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"Unexpected error deleting history for {date_str}: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
    finally:
        if conn:
            conn.close()


# --- Context Menu Helper Routes ---

@app.route('/list_files')
def list_files_endpoint():
    """Recursively list all files within ALLOWED_CONTEXT_DIR."""
    all_files = []
    if not ALLOWED_CONTEXT_DIR or not os.path.exists(ALLOWED_CONTEXT_DIR):
        print(f"Warning: ALLOWED_CONTEXT_DIR ('{ALLOWED_CONTEXT_DIR}') not found for listing files.")
        return jsonify([])

    try:
        for root, dirs, files in os.walk(ALLOWED_CONTEXT_DIR):
            # Security: Skip if root somehow goes outside allowed dir (shouldn't happen with os.walk)
            if not os.path.realpath(root).lower().startswith(ALLOWED_CONTEXT_DIR.lower()):
                continue
            for filename in files:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, ALLOWED_CONTEXT_DIR)
                # Use forward slashes for display
                all_files.append(relative_path.replace(os.path.sep, '/'))
    except Exception as e:
        print(f"Error listing files in '{ALLOWED_CONTEXT_DIR}': {e}")
        return jsonify({"error": f"Failed to list files: {e}"}), 500

    return jsonify(sorted(all_files))

@app.route('/list_folders')
def list_folders_endpoint():
    """Recursively list all folders within ALLOWED_CONTEXT_DIR."""
    all_folders = []
    if not ALLOWED_CONTEXT_DIR or not os.path.exists(ALLOWED_CONTEXT_DIR):
        print(f"Warning: ALLOWED_CONTEXT_DIR ('{ALLOWED_CONTEXT_DIR}') not found for listing folders.")
        return jsonify([])

    try:
        for root, dirs, files in os.walk(ALLOWED_CONTEXT_DIR):
             # Security: Skip if root somehow goes outside allowed dir
            if not os.path.realpath(root).lower().startswith(ALLOWED_CONTEXT_DIR.lower()):
                continue
            for dirname in dirs:
                full_path = os.path.join(root, dirname)
                relative_path = os.path.relpath(full_path, ALLOWED_CONTEXT_DIR)
                # Use forward slashes and add trailing slash for display
                all_folders.append(relative_path.replace(os.path.sep, '/') + '/')
    except Exception as e:
        print(f"Error listing folders in '{ALLOWED_CONTEXT_DIR}': {e}")
        return jsonify({"error": f"Failed to list folders: {e}"}), 500

    # Add the root directory itself if needed (represented as './' or just '/')
    # Let's keep it simple and only list subfolders for now.
    # If the root itself needs to be selectable, the frontend logic might need adjustment.

    return jsonify(sorted(all_folders))


# --- Path Suggestion Route (Kept for potential future use or different trigger) ---
@app.route('/suggest_path')
def suggest_path():
    """Provide suggestions for file/folder paths within ALLOWED_CONTEXT_DIR."""
    partial_path = request.args.get('partial', '')
    suggestions = []
    max_suggestions = 15 # Limit the number of suggestions

    if not ALLOWED_CONTEXT_DIR or not os.path.exists(ALLOWED_CONTEXT_DIR):
        print("Warning: ALLOWED_CONTEXT_DIR not found or not accessible for suggestions.")
        return jsonify([]) # Return empty list if base dir is invalid

    try:
        # Normalize the partial path (handle both / and \ separators)
        normalized_partial = os.path.normpath(partial_path.strip().strip("'\""))

        # Prevent accessing parent directories or absolute paths
        if os.path.isabs(normalized_partial) or ".." in normalized_partial.split(os.path.sep):
            return jsonify([]) # Return empty for invalid/unsafe paths

        # Determine the directory to search and the prefix to match
        if os.path.sep in normalized_partial:
            # User is typing a path within a subdirectory
            base_dir_part, search_prefix = os.path.split(normalized_partial)
            search_dir = os.path.realpath(os.path.join(ALLOWED_CONTEXT_DIR, base_dir_part))
        else:
            # User is typing at the root of allowed_context
            base_dir_part = ""
            search_prefix = normalized_partial
            search_dir = ALLOWED_CONTEXT_DIR

        # Security Check: Ensure the search directory is still within the allowed directory
        if not search_dir.startswith(ALLOWED_CONTEXT_DIR + os.path.sep) and search_dir != ALLOWED_CONTEXT_DIR:
             print(f"Warning: Suggestion path '{search_dir}' resolved outside allowed directory.")
             return jsonify([])

        if not os.path.isdir(search_dir):
            return jsonify([]) # Base directory doesn't exist or isn't a directory

        # List items and filter based on the prefix
        count = 0
        for item in sorted(os.listdir(search_dir)):
            if item.lower().startswith(search_prefix.lower()):
                full_item_path = os.path.join(search_dir, item)
                # Construct the suggestion path relative to the original partial input
                suggestion = os.path.join(base_dir_part, item)
                # Use forward slashes for consistency in suggestions, even on Windows
                suggestion = suggestion.replace(os.path.sep, '/')

                if os.path.isdir(full_item_path):
                    suggestions.append(suggestion + "/") # Add trailing slash for directories
                else:
                    suggestions.append(suggestion)
                count += 1
                if count >= max_suggestions:
                    break

    except FileNotFoundError:
        # This might happen if the base_dir_part doesn't exist, which is fine.
        pass # Return empty suggestions
    except Exception as e:
        print(f"Error generating path suggestions for '{partial_path}': {e}")
        # Don't expose internal errors, just return empty list
        return jsonify([])

    # print(f"Suggestions for '{partial_path}': {suggestions}") # Debug log
    return jsonify(suggestions)


if __name__ == '__main__':
    # Make sure .env is in the same directory or GOOGLE_API_KEY is set globally
    print("Starting Flask server...")
    print("Ensure GOOGLE_API_KEY is set in a .env file or environment variables.")
    print(f"Database file: {os.path.abspath(DB_NAME)}")
    # Use debug=True for development, but turn off in production
    # Use host='0.0.0.0' to make it accessible on the network
    app.run(debug=True, host='0.0.0.0', port=5000)
