import os
from flask import Blueprint, jsonify, request, json

# Import shared utilities and config
import config # Import config module directly
from config import DEFAULT_MODEL_NAME # Keep this direct import
from context_processing import fetch_and_process_url, process_context_path
from gemini_utils import get_available_models, generate_summary

# Create Blueprint
context_bp = Blueprint('context', __name__)

@context_bp.route('/list_files')
def list_files_endpoint():
    """API endpoint to recursively list all files within ALLOWED_CONTEXT_DIR."""
    all_files = []
    if not config.ALLOWED_CONTEXT_DIR or not os.path.exists(config.ALLOWED_CONTEXT_DIR): # Use config.ALLOWED_CONTEXT_DIR
        print(f"Warning: ALLOWED_CONTEXT_DIR ('{config.ALLOWED_CONTEXT_DIR}') not found for listing files.") # Use config.ALLOWED_CONTEXT_DIR
        return jsonify([]) # Return empty list if dir doesn't exist

    try:
        allowed_dir_real = os.path.realpath(config.ALLOWED_CONTEXT_DIR) # Use config.ALLOWED_CONTEXT_DIR
        for root, dirs, files in os.walk(allowed_dir_real):
            # Security check: Ensure we don't somehow walk outside the allowed dir
            current_root_real = os.path.realpath(root)
            if os.name == 'nt': # Windows case-insensitive check
                 if not current_root_real.lower().startswith(allowed_dir_real.lower()):
                     print(f"Warning: Skipping directory outside allowed root: {current_root_real}")
                     continue
            else: # Case-sensitive check
                 if not current_root_real.startswith(allowed_dir_real):
                     print(f"Warning: Skipping directory outside allowed root: {current_root_real}")
                     continue

            for filename in files:
                try:
                    full_path = os.path.join(root, filename)
                    # Calculate path relative to the *original* ALLOWED_CONTEXT_DIR for consistency
                    relative_path = os.path.relpath(full_path, allowed_dir_real)
                    # Use forward slashes for display consistency across OS
                    all_files.append(relative_path.replace(os.path.sep, '/'))
                except Exception as item_e:
                     print(f"Error processing file item '{filename}' in '{root}': {item_e}")
                     # Optionally skip this file and continue

    except Exception as e:
        print(f"Error listing files in '{config.ALLOWED_CONTEXT_DIR}': {e}") # Use config.ALLOWED_CONTEXT_DIR
        return jsonify({"error": f"Failed to list files: {e}"}), 500

    return jsonify(sorted(all_files))

@context_bp.route('/list_folders')
def list_folders_endpoint():
    """API endpoint to recursively list all folders within ALLOWED_CONTEXT_DIR."""
    all_folders = []
    if not config.ALLOWED_CONTEXT_DIR or not os.path.exists(config.ALLOWED_CONTEXT_DIR): # Use config.ALLOWED_CONTEXT_DIR
        print(f"Warning: ALLOWED_CONTEXT_DIR ('{config.ALLOWED_CONTEXT_DIR}') not found for listing folders.") # Use config.ALLOWED_CONTEXT_DIR
        return jsonify([])

    try:
        allowed_dir_real = os.path.realpath(config.ALLOWED_CONTEXT_DIR) # Use config.ALLOWED_CONTEXT_DIR
        for root, dirs, files in os.walk(allowed_dir_real):
            # Security check (similar to list_files)
            current_root_real = os.path.realpath(root)
            if os.name == 'nt':
                 if not current_root_real.lower().startswith(allowed_dir_real.lower()):
                     print(f"Warning: Skipping directory outside allowed root: {current_root_real}")
                     continue
            else:
                 if not current_root_real.startswith(allowed_dir_real):
                     print(f"Warning: Skipping directory outside allowed root: {current_root_real}")
                     continue

            for dirname in dirs:
                try:
                    full_path = os.path.join(root, dirname)
                    relative_path = os.path.relpath(full_path, allowed_dir_real)
                    # Use forward slashes and add trailing slash for display
                    all_folders.append(relative_path.replace(os.path.sep, '/') + '/')
                except Exception as item_e:
                     print(f"Error processing directory item '{dirname}' in '{root}': {item_e}")

    except Exception as e:
        print(f"Error listing folders in '{config.ALLOWED_CONTEXT_DIR}': {e}") # Use config.ALLOWED_CONTEXT_DIR
        return jsonify({"error": f"Failed to list folders: {e}"}), 500

    # Add the root directory itself, represented by './'
    all_folders.append('./')

    return jsonify(sorted(all_folders))


@context_bp.route('/suggest_path')
def suggest_path_endpoint():
    """API endpoint to provide suggestions for file/folder paths within ALLOWED_CONTEXT_DIR."""
    partial_path = request.args.get('partial', '')
    suggestions = []
    max_suggestions = 20 # Limit the number of suggestions

    if not config.ALLOWED_CONTEXT_DIR or not os.path.exists(config.ALLOWED_CONTEXT_DIR): # Use config.ALLOWED_CONTEXT_DIR
        print("Warning: ALLOWED_CONTEXT_DIR not found or not accessible for suggestions.")
        return jsonify([]) # Return empty list if base dir is invalid

    try:
        # Normalize the partial path (handle both / and \ separators, remove quotes)
        normalized_partial = os.path.normpath(partial_path.strip().strip("'\""))

        # Security Check: Prevent accessing parent directories or absolute paths
        if os.path.isabs(normalized_partial) or ".." in normalized_partial.split(os.path.sep):
            return jsonify([]) # Return empty for invalid/unsafe paths

        # Determine the directory to search and the prefix to match
        if os.path.sep in normalized_partial or '/' in normalized_partial: # Check both separators
            # User is typing a path within a subdirectory
            base_dir_part, search_prefix = os.path.split(normalized_partial)
            # Construct search directory path relative to allowed dir
            search_dir_relative = base_dir_part
        else:
            # User is typing at the root of allowed_context
            base_dir_part = ""
            search_prefix = normalized_partial
            if search_prefix == ".": # If normpath("") made it ".", treat as empty for prefix matching
                search_prefix = ""
            search_dir_relative = "" # Search in the root

        # Resolve the actual search directory path securely
        allowed_dir_real = os.path.realpath(config.ALLOWED_CONTEXT_DIR) # Use config.ALLOWED_CONTEXT_DIR
        search_dir_absolute = os.path.realpath(os.path.join(allowed_dir_real, search_dir_relative))

        # Security Check: Ensure the search directory is still within the allowed directory
        if os.name == 'nt':
             if not search_dir_absolute.lower().startswith(allowed_dir_real.lower()):
                 print(f"Warning: Suggestion path '{search_dir_absolute}' resolved outside allowed directory.")
                 return jsonify([])
        else:
             if not search_dir_absolute.startswith(allowed_dir_real):
                 print(f"Warning: Suggestion path '{search_dir_absolute}' resolved outside allowed directory.")
                 return jsonify([])

        if not os.path.isdir(search_dir_absolute):
            return jsonify([]) # Base directory doesn't exist or isn't a directory

        # List items and filter based on the prefix
        count = 0
        for item in sorted(os.listdir(search_dir_absolute)):
            if item.lower().startswith(search_prefix.lower()):
                full_item_path_absolute = os.path.join(search_dir_absolute, item)
                # Construct the suggestion path relative to the *allowed context root*
                suggestion_relative_to_root = os.path.relpath(full_item_path_absolute, allowed_dir_real)

                # Use forward slashes for consistency in suggestions
                suggestion = suggestion_relative_to_root.replace(os.path.sep, '/')

                if os.path.isdir(full_item_path_absolute):
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


@context_bp.route('/summarize_context', methods=['POST'])
def summarize_context_endpoint():
    """API endpoint to summarize a list of provided context items (files/folders/URLs)."""
    data = request.json
    if not data or 'context_items' not in data:
        return jsonify({"error": "No context items provided"}), 400

    context_items = data.get('context_items', [])
    if not isinstance(context_items, list) or not context_items:
        return jsonify({"error": "Invalid or empty context items list"}), 400

    # Get selected model from request or use default
    selected_model_name = data.get('model_name', DEFAULT_MODEL_NAME)
    available_models = get_available_models() # Use cache
    if selected_model_name not in available_models:
         # Don't refresh here, just return error if invalid model was sent
         return jsonify({"error": f"Invalid model selected for summary: {selected_model_name}. Available: {available_models}"}), 400

    # Process each context item and gather their content
    full_context = ""
    errors = []
    processed_paths_info_summary = [] # Separate tracking for summary context

    for item in context_items:
        context_part = ""
        error = None
        path_info = None
        try:
            if item.startswith(('http://', 'https://')):
                context_part, error, path_info = fetch_and_process_url(item)
            else:
                context_part, error, path_info = process_context_path(item)

            if path_info:
                processed_paths_info_summary.append(path_info) # Log attempt
            if error:
                errors.append(path_info.get("message") or f"Error processing: {item}")
            if context_part:
                full_context += context_part

        except Exception as e:
            error_msg = f"Unexpected error processing context item '{item}' for summary: {e}"
            print(error_msg)
            errors.append(error_msg)
            processed_paths_info_summary.append({
                 "original": item, "status": "error", "message": error_msg
            })


    if not full_context and not errors:
         # If no context could be gathered and no errors occurred (e.g., all items were empty)
         return jsonify({"error": "No content found in provided context items to summarize."}), 400
    elif not full_context and errors:
         # If no context was gathered but errors occurred
         return jsonify({"error": "Failed to process context items for summary.", "details": errors}), 400

    # --- Generate Summary ---
    try:
        # Create a prompt that asks for a summary
        # Limit the context sent to the model if it's excessively large?
        # For now, send all gathered context. Consider truncation if needed.
        prompt = f"""Please provide a concise summary of the following context obtained from {len(context_items)} source(s):

{full_context}

Focus on the main topics, key information, structure, and any potential issues or highlights.
Keep the summary clear and well-organized."""

        # Use the non-streaming generation utility
        summary = generate_summary(prompt, selected_model_name)

        response_data = {"summary": summary, "processed_items": processed_paths_info_summary}
        if errors:
            # Include any non-fatal processing errors as warnings
            response_data["warnings"] = errors

        return jsonify(response_data)

    except Exception as e:
        # Catch errors from generate_summary (model instantiation or API call)
        print(f"Error generating context summary with model {selected_model_name}: {e}")
        # Return a specific error message to the client, including details
        return jsonify({"error": f"Failed to generate summary using model {selected_model_name}.", "details": str(e)}), 500
