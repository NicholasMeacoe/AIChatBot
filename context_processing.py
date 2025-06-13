import os
import requests
from bs4 import BeautifulSoup
import html
import config # Import the config module directly
# Remove direct imports of constants that need to be monkeypatched
from config import (
    # ALLOWED_CONTEXT_DIR,
    # ALLOWED_CONTEXT_DIR_NAME,
    # MAX_FILE_READ_BYTES, # Will access via config.MAX_FILE_READ_BYTES
    MAX_FILE_SIZE_MB, # This one seems okay for now, or change if needed
    # MAX_URL_CONTENT_BYTES, # Will access via config.MAX_URL_CONTENT_BYTES
    REQUEST_TIMEOUT # Likely okay, but for consistency could also be config.REQUEST_TIMEOUT
)

# --- URL Fetching and Processing ---

def fetch_and_process_url(url):
    """
    Fetches content from a URL, extracts text, and handles errors.
    Returns a tuple: (context_string, error_message, processed_url_info_dict)
    """
    context_str = ""
    error_msg = None
    # Provides detailed info about the outcome for logging/debugging
    processed_url_info = {
        "original": url,
        "status": "error", # Default status
        "message": None,
        "context_added": False
    }

    try:
        headers = { # Mimic a browser to avoid simple blocks
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Use stream=True to handle large responses and check headers first
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        content_type = response.headers.get('content-type', '').lower()

        # Basic check for HTML/Text content before downloading fully
        if 'html' in content_type or 'text' in content_type:
            content = b""
            bytes_read = 0
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                bytes_read += len(chunk)
                if bytes_read > config.MAX_URL_CONTENT_BYTES: # Use config.MAX_URL_CONTENT_BYTES
                    error_msg = f"Error: URL content exceeds limit ({config.MAX_URL_CONTENT_BYTES / (1024*1024):.1f} MB). Truncated." # Use config.MAX_URL_CONTENT_BYTES
                    processed_url_info["message"] = error_msg
                    break # Stop reading

            # Decode content (attempt common encodings)
            try:
                decoded_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    decoded_content = content.decode('iso-8859-1')
                except UnicodeDecodeError:
                    # Fallback, ignoring errors might lose some characters
                    decoded_content = content.decode('ascii', errors='ignore')

            # Extract text using BeautifulSoup for HTML
            if 'html' in content_type:
                soup = BeautifulSoup(decoded_content, 'html.parser')
                # Remove script and style elements which don't usually contain useful context
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                # Get text, strip leading/trailing whitespace from each string, join with spaces
                text = ' '.join(soup.stripped_strings)
            else: # Plain text
                text = decoded_content.strip() # Strip whitespace from plain text

            # Add context header/footer
            context_str += f"--- START CONTEXT FROM URL: {url} ---\n"
            # Ensure final text doesn't exceed limit again after potential BS4 processing
            context_str += text[:config.MAX_URL_CONTENT_BYTES] # Use config.MAX_URL_CONTENT_BYTES
            if error_msg: # Append truncation warning if it occurred
                 context_str += "\n... (Content Truncated)"
            context_str += f"\n--- END CONTEXT FROM URL: {url} ---\n\n"

            processed_url_info["status"] = "ok"
            processed_url_info["context_added"] = True
            # Keep the truncation message if it occurred
            if error_msg:
                 processed_url_info["message"] = error_msg

        else:
            error_msg = f"Error: Unsupported content type '{content_type}' for URL: {url}. Only HTML/Text supported."
            processed_url_info["message"] = error_msg

    except requests.exceptions.Timeout:
        error_msg = f"Error: Timeout fetching URL: {url} (>{config.REQUEST_TIMEOUT}s)" # Use config.REQUEST_TIMEOUT
        processed_url_info["message"] = error_msg
    except requests.exceptions.RequestException as e:
        # Catch connection errors, invalid URLs, status code errors, etc.
        error_msg = f"Error fetching URL {url}: {e}"
        processed_url_info["message"] = error_msg
    except Exception as e:
        # Catch potential errors during content processing (decoding, BS4)
        error_msg = f"Error processing URL {url}: {e}"
        processed_url_info["message"] = error_msg

    # Ensure context_str is empty if a significant error occurred
    if error_msg and processed_url_info["status"] == "error":
        context_str = ""
        processed_url_info["context_added"] = False


    return context_str, error_msg, processed_url_info


# --- File/Folder Path Processing ---

def process_context_path(path):
    """
    Reads content from a file or lists contents of a folder within the ALLOWED_CONTEXT_DIR.
    Performs security checks to prevent accessing files outside the allowed directory.
    Returns a tuple: (context_string, error_message, processed_path_info_dict)
    """
    context_str = ""
    error_msg = None
    # Provides detailed info about the outcome for logging/debugging
    processed_path_info = {
        "original": path,
        "resolved": None, # The actual filesystem path checked
        "status": "error", # Default status
        "message": None,
        "context_added": False
    }

    if not config.ALLOWED_CONTEXT_DIR: # Use config.ALLOWED_CONTEXT_DIR
        error_msg = "Error: The allowed context directory is not configured or accessible."
        processed_path_info["message"] = error_msg
        return context_str, error_msg, processed_path_info

    # Basic input cleaning
    clean_path = path.strip().strip("'\"")

    # Security Check 1: Prevent absolute paths and path traversal attempts
    # os.path.normpath helps normalize separators but doesn't prevent '..'
    normalized_path = os.path.normpath(clean_path)
    if os.path.isabs(normalized_path) or ".." in normalized_path.split(os.path.sep):
         error_msg = f"Error: Only relative paths within '{config.ALLOWED_CONTEXT_DIR_NAME}' are allowed. Path traversal ('..') or absolute paths are forbidden: '{path}'" # Use config.ALLOWED_CONTEXT_DIR_NAME
         processed_path_info["message"] = error_msg
         return context_str, error_msg, processed_path_info

    # Construct the full path securely within the allowed directory
    # os.path.join correctly handles path separators for the OS
    # os.path.abspath resolves the path, making it absolute
    # os.path.realpath resolves any symbolic links (important for security)
    try:
        # Ensure config.ALLOWED_CONTEXT_DIR exists before joining
        if not os.path.isdir(config.ALLOWED_CONTEXT_DIR): # Use config.ALLOWED_CONTEXT_DIR
             error_msg = f"Error: Allowed context directory '{config.ALLOWED_CONTEXT_DIR}' does not exist." # Use config.ALLOWED_CONTEXT_DIR
             processed_path_info["message"] = error_msg
             return context_str, error_msg, processed_path_info

        target_path_intermediate = os.path.join(config.ALLOWED_CONTEXT_DIR, normalized_path) # Use config.ALLOWED_CONTEXT_DIR
        target_path = os.path.realpath(target_path_intermediate)
        processed_path_info["resolved"] = target_path # Store the actual path we are checking
    except Exception as e:
         error_msg = f"Error resolving path '{path}': {e}"
         processed_path_info["message"] = error_msg
         return context_str, error_msg, processed_path_info


    # Security Check 2: Ensure the resolved path is *still* within the allowed directory
    # This comparison must be case-insensitive on Windows
    allowed_dir_real = os.path.realpath(config.ALLOWED_CONTEXT_DIR) # Use config.ALLOWED_CONTEXT_DIR
    if os.name == 'nt': # Windows
        if not target_path.lower().startswith(allowed_dir_real.lower() + os.path.sep) and \
           target_path.lower() != allowed_dir_real.lower():
            error_msg = f"Error: Access denied. Path '{path}' resolves outside the allowed directory '{config.ALLOWED_CONTEXT_DIR_NAME}'." # Use config.ALLOWED_CONTEXT_DIR_NAME
            processed_path_info["message"] = error_msg
            return context_str, error_msg, processed_path_info
    else: # Linux/macOS (case-sensitive paths)
        if not target_path.startswith(allowed_dir_real + os.path.sep) and \
           target_path != allowed_dir_real:
            error_msg = f"Error: Access denied. Path '{path}' resolves outside the allowed directory '{config.ALLOWED_CONTEXT_DIR_NAME}'." # Use config.ALLOWED_CONTEXT_DIR_NAME
            processed_path_info["message"] = error_msg
            return context_str, error_msg, processed_path_info


    # Check if the resolved path actually exists
    if not os.path.exists(target_path):
        # Use the user-provided 'clean_path' in the error message for clarity
        error_msg = f"Error: Path not found within '{config.ALLOWED_CONTEXT_DIR_NAME}': '{clean_path}' (resolved to '{target_path}')" # Use config.ALLOWED_CONTEXT_DIR_NAME
        processed_path_info["message"] = error_msg
        return context_str, error_msg, processed_path_info

    try:
        # Get path relative to allowed dir for user-friendly display/context headers
        relative_display_path = os.path.relpath(target_path, allowed_dir_real)
        # Use forward slashes for display consistency
        relative_display_path = relative_display_path.replace(os.path.sep, '/')

        if os.path.isfile(target_path):
            file_size = os.path.getsize(target_path)
            if file_size > config.MAX_FILE_READ_BYTES: # Use config.MAX_FILE_READ_BYTES
                 error_msg = (f"Error: File '{relative_display_path}' is too large "
                              f"({file_size / (1024*1024):.2f} MB > "
                              # Message shows MAX_FILE_SIZE_MB, but logic uses MAX_FILE_READ_BYTES. Keep message for now or align.
                              f"{config.MAX_FILE_SIZE_MB} MB limit). Skipping.")
                 processed_path_info["message"] = error_msg
                 # Return empty context but no error_msg that halts processing other items
                 return "", error_msg, processed_path_info

            context_str += f"--- START CONTEXT FROM FILE: {relative_display_path} ---\n"
            try:
                # Read with UTF-8, ignore errors for robustness against encoding issues
                with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                    context_str += f.read(config.MAX_FILE_READ_BYTES) # Use config.MAX_FILE_READ_BYTES
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
                    MAX_FILES_IN_DIR_LISTING = 50
                    count = 0
                    items.sort() # List items predictably
                    for item in items:
                        if count >= MAX_FILES_IN_DIR_LISTING:
                            context_str += f"... (truncated listing at {MAX_FILES_IN_DIR_LISTING} items)\n"
                            break

                        item_full_path = os.path.join(target_path, item)
                        item_rel_path = os.path.join(relative_display_path, item).replace(os.path.sep, '/')

                        # Basic check if item exists (might have been deleted between listdir and check)
                        if not os.path.exists(item_full_path):
                            context_str += f"--- SKIPPING ITEM (not found): {item_rel_path} ---\n"
                            continue

                        # Security check: Ensure listed item is still within allowed dir (paranoid check)
                        item_real_path = os.path.realpath(item_full_path)
                        if os.name == 'nt':
                            if not item_real_path.lower().startswith(allowed_dir_real.lower() + os.path.sep):
                                context_str += f"--- SKIPPING ITEM (outside allowed dir): {item_rel_path} ---\n"
                                continue
                        else:
                            if not item_real_path.startswith(allowed_dir_real + os.path.sep):
                                context_str += f"--- SKIPPING ITEM (outside allowed dir): {item_rel_path} ---\n"
                                continue

                        if os.path.isfile(item_full_path):
                            try:
                                file_size = os.path.getsize(item_full_path)
                                size_kb = file_size / 1024
                                if file_size > config.MAX_FILE_READ_BYTES: # Use config.MAX_FILE_READ_BYTES
                                    context_str += f"- {item_rel_path} [File] (SKIPPED - Too large: {size_kb / 1024:.2f} MB)\n"
                                else:
                                    context_str += f"- {item_rel_path} [File] ({size_kb:.1f} KB)\n"
                                    count += 1
                            except Exception as e:
                                context_str += f"- {item_rel_path} [File] (ERROR accessing: {e})\n"
                        elif os.path.isdir(item_full_path):
                            context_str += f"- {item_rel_path}/ [DIR]\n"
                            count += 1
                        # else: ignore other types like symlinks, etc. in listing

            except Exception as e:
                 error_msg = f"Error processing directory '{relative_display_path}': {e}"
                 processed_path_info["message"] = error_msg
                 return "", error_msg, processed_path_info # Return empty context on error
            context_str += f"--- END CONTEXT FROM FOLDER CONTENTS: {relative_display_path}/ ---\n\n"
            processed_path_info["status"] = "ok"
            # Context is considered added if the folder exists, even if empty or only contains errors/skipped items
            processed_path_info["context_added"] = True

        else:
            # This case should technically not be reached due to os.path.exists check
            error_msg = f"Error: Path '{relative_display_path}' exists but is not a file or directory."
            processed_path_info["message"] = error_msg


    except Exception as e:
        # Catch-all for unexpected errors during processing
        error_msg = f"Unexpected error processing path '{path}': {e}"
        processed_path_info["message"] = error_msg

    # If context_str is empty but no critical error occurred (e.g., empty file/dir, skipped large file), set status ok
    if not error_msg and not context_str and processed_path_info["status"] != "ok":
         processed_path_info["status"] = "ok"
         processed_path_info["context_added"] = False # No actual content was added
         processed_path_info["message"] = processed_path_info.get("message") or "Path found but contained no readable context (e.g., empty file/directory, skipped large file)."
         # Don't set error_msg here, let the calling function decide based on status/message

    # Ensure context_str is empty if a critical error occurred
    if error_msg and processed_path_info["status"] == "error":
        context_str = ""
        processed_path_info["context_added"] = False

    return context_str, error_msg, processed_path_info

# Note: parse_input_for_context is removed from here.
# It deals more with request parsing and orchestrating calls to
# process_context_path/fetch_and_process_url, so it fits better
# within the routing logic or a dedicated request handling module.
