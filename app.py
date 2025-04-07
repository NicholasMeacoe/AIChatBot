from flask import Flask, render_template, request, Response, stream_with_context
import google.generativeai as genai
import os
import re
import sqlite3
import json
from dotenv import load_dotenv
from datetime import datetime

# --- Configuration ---
MODEL_NAME = "gemini-2.5-pro-exp-03-25"
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

# --- Gemini Chatbot Logic (Adapted from GeminiChatBot.py) ---

# Load API Key (Simplified for server environment - expects .env)
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    # In a real app, you might want to handle this more gracefully
    # For now, we'll let it fail later if the key is missing.
else:
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
        print(f"Gemini model '{MODEL_NAME}' initialized.")
    except Exception as e:
        print(f"Error initializing Gemini model: {e}")
        model = None # Ensure model is None if init fails

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

    return full_context, cleaned_message, errors, processed_paths_info


# --- Flask Routes ---

@app.route('/')
def index():
    """Render the main chat page and load history."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_message, bot_response, timestamp FROM history ORDER BY timestamp ASC")
    history = cursor.fetchall()
    conn.close()
    return render_template('index.html', history=history)

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Handle incoming chat messages and stream responses."""
    if not model:
         return Response(json.dumps({"error": "Gemini model not initialized. Check API Key and logs."}), status=500, mimetype='application/json')

    user_message = request.json.get('message')
    if not user_message:
        return Response(json.dumps({"error": "No message provided."}), status=400, mimetype='application/json')

    # --- Context Processing ---
    file_context, cleaned_prompt, context_errors, processed_paths = parse_input_for_context(user_message)
    context_info_json = json.dumps(processed_paths) if processed_paths else None

    # Construct the final prompt
    final_prompt = file_context + cleaned_prompt if file_context else cleaned_prompt

    if not final_prompt.strip():
         # If only context errors occurred, return them
         if context_errors:
             error_response = "\n".join(context_errors)
             return Response(json.dumps({"error": f"Context processing failed:\n{error_response}"}), status=400, mimetype='application/json')
         else: # Should not happen if parse_input handles empty cases
             return Response(json.dumps({"error": "Cannot send an empty message after context processing."}), status=400, mimetype='application/json')

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
            # To enable streaming: use stream=True
            stream = model.generate_content(final_prompt, stream=True)
            
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
                (user_message, full_bot_response, context_info_json) # Store original user message
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


if __name__ == '__main__':
    # Make sure .env is in the same directory or GOOGLE_API_KEY is set globally
    print("Starting Flask server...")
    print("Ensure GOOGLE_API_KEY is set in a .env file or environment variables.")
    print(f"Database file: {os.path.abspath(DB_NAME)}")
    # Use debug=True for development, but turn off in production
    # Use host='0.0.0.0' to make it accessible on the network
    app.run(debug=True, host='0.0.0.0', port=5000)
