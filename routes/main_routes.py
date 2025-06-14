from flask import (
    Blueprint, render_template, request, Response, stream_with_context,
    jsonify, json
)
from datetime import datetime

# Import shared utilities and config
import config # Import the config module directly
from config import DEFAULT_MODEL_NAME, FREE_TIER_LIMITS # Keep direct imports for these
# GOOGLE_API_KEY will be accessed via config.GOOGLE_API_KEY
from database import (
    get_chat_history, get_distinct_chat_dates, save_chat_history,
    delete_history_by_date
)
from gemini_utils import get_available_models, generate_response_stream
from context_processing import fetch_and_process_url, process_context_path

# Create Blueprint
main_bp = Blueprint('main', __name__, template_folder='../templates') # Point to parent templates folder

@main_bp.route('/')
def index():
    """Render the main chat page and load history, optionally filtered by date."""
    available_dates = get_distinct_chat_dates()
    selected_date = request.args.get('date') # Get selected date from query parameters

    # Fetch history ONLY if a date is selected
    history = [] # Default to empty history
    if selected_date:
        history = get_chat_history(selected_date) # Fetch only if date is specified

    # Get available models (use cached list)
    available_models = get_available_models()

    return render_template(
        'index.html',
        history=history,
        available_dates=available_dates,
        selected_date=selected_date,
        available_models=available_models,
        default_model=DEFAULT_MODEL_NAME,
        usage_limits=FREE_TIER_LIMITS # Pass limits for display
    )

@main_bp.route('/chat', methods=['POST'])
def chat_endpoint():
    """Handle incoming chat messages and stream responses."""
    if not config.GOOGLE_API_KEY: # Access dynamically
         # Ensure API key check happens early
         return Response(json.dumps({"error": "Gemini API Key not configured."}), status=500, mimetype='application/json')

    data = request.json
    user_message = data.get('message')
    active_context_items = data.get('active_context', []) # Get active context list
    selected_model_name = data.get('model_name', DEFAULT_MODEL_NAME)

    if not user_message and not active_context_items: # Need either message or context
        return Response(json.dumps({"error": "No message or context provided."}), status=400, mimetype='application/json')

    # Validate selected model against the fetched list
    available_models = get_available_models() # Use cached list
    if selected_model_name not in available_models:
        # Attempt to refresh the list *once* if model not found
        print(f"Selected model '{selected_model_name}' not in cached list, attempting refresh...")
        available_models = get_available_models(force_refresh=True)
        if selected_model_name not in available_models:
             print(f"Error: Invalid model selected even after refresh: {selected_model_name}")
             return Response(json.dumps({"error": f"Invalid model selected: {selected_model_name}. Available: {available_models}"}), status=400, mimetype='application/json')

    # --- Process Active Context Items ---
    context_errors_for_sse = [] # For yielding SSE events
    processed_context_info_for_db = [] # Store detailed info for DB logging
    context_parts_for_prompt = [] # Collect parts for the final prompt (successful context + specific errors)

    if active_context_items:
        print(f"Processing active context: {active_context_items}")
        for item_path in active_context_items:
            context_part_content = "" # Content from successful processing
            error_message_for_prompt = None # Specific error message for this item for the prompt
            path_info = None # Holds original, status, message etc. from processing functions

            try:
                if item_path.startswith(('http://', 'https://')):
                    context_part_content, error, path_info = fetch_and_process_url(item_path)
                else:
                    context_part_content, error, path_info = process_context_path(item_path)

                if path_info: # path_info should always be returned
                    processed_context_info_for_db.append(path_info)
                else: # Should not happen if processing functions are consistent
                    path_info = {"original": item_path, "status": "error", "message": "Processing function returned no info"}
                    processed_context_info_for_db.append(path_info)


                if error: # An error occurred for this item
                    # For SSE event (general client display)
                    error_message_for_sse = path_info.get("message") or f"Error processing: {item_path}"
                    context_errors_for_sse.append(error_message_for_sse)
                    # For prompt construction (more detailed, as per test expectations)
                    # This format matches test_chat_endpoint_context_error_handling's expected_prompt
                    error_message_for_prompt = f"Error processing context for {path_info.get('original', item_path)}: {path_info.get('message', 'Unknown error')}. "
                    context_parts_for_prompt.append(error_message_for_prompt)

                if context_part_content: # Successful context processing for this item
                    context_parts_for_prompt.append(context_part_content)

            except Exception as e:
                 # Catch unexpected errors during an item's context processing
                 error_msg = f"Unexpected error processing context item '{item_path}': {e}"
                 print(error_msg)
                 context_errors_for_sse.append(error_msg) # Add to SSE errors
                 # Add a corresponding error message to the prompt parts
                 context_parts_for_prompt.append(f"Error processing context for {item_path}: {error_msg}. ")
                 # Ensure something is added to DB logs
                 if not path_info: # If path_info wasn't set before exception
                     processed_context_info_for_db.append({
                         "original": item_path, "status": "error", "message": error_msg
                     })

    full_context_str = "".join(context_parts_for_prompt) # Construct final context string from all parts

    # --- Construct Final Prompt ---
    # Use a placeholder if user message is empty but context exists
    display_user_message = user_message if user_message else "(Referring to provided context)"
    final_prompt = full_context_str + display_user_message # Prepend context string (which now includes errors)

    # Store original user message (even if empty) and context info for DB
    original_user_message_for_db = user_message if user_message else ""

    # --- Streaming Response ---
    def generate_and_save():
        # Yield context errors as separate SSE events first, if any (for client display)
        if context_errors_for_sse:
            sse_error_data = json.dumps({"context_error": "\n".join(context_errors_for_sse)})
            yield f"data: {sse_error_data}\n\n"

        # Use the utility function for streaming generation
        full_bot_response = ""
        try:
            # generate_response_stream handles model instantiation and errors
            for chunk_data in generate_response_stream(final_prompt, selected_model_name):
                yield chunk_data # Pass through the SSE data
                # Try to capture the text part for saving
                try:
                    data_dict = json.loads(chunk_data.split("data: ")[1])
                    if "text" in data_dict:
                        full_bot_response += data_dict["text"]
                    elif "error" in data_dict:
                         # If an error occurred during generation, stop trying to save
                         print(f"Generation error received: {data_dict['error']}")
                         return # Stop the generator
                except (IndexError, json.JSONDecodeError):
                    pass # Ignore malformed data for saving purpose

            # --- Save to Database ---
            # Save only if generation seemed successful (no error yielded by stream)
            if full_bot_response: # Check if we got any response text
                save_chat_history(
                    original_user_message_for_db,
                    full_bot_response,
                    processed_context_info_for_db
                )
            else:
                print("Skipping DB save as bot response was empty or generation failed.")

        except Exception as e:
            # This catches errors *before* streaming starts (e.g., model init)
            # Errors *during* streaming are handled within generate_response_stream
            print(f"Error setting up or during chat generation stream: {e}")
            error_data = json.dumps({"error": f"An error occurred: {e}"})
            yield f"data: {error_data}\n\n"

    # Use stream_with_context for generators
    return Response(stream_with_context(generate_and_save()), mimetype='text/event-stream')


@main_bp.route('/fetch_history', methods=['GET'])
def fetch_history_endpoint():
    """API endpoint to fetch chat history for a specific date or all history."""
    selected_date = request.args.get('date')
    try:
        # get_chat_history handles date validation and HTML escaping
        history_list = get_chat_history(selected_date)
        return jsonify({'history': history_list})
    except Exception as e:
        # Catch unexpected errors during fetch
        print(f"Error in /fetch_history endpoint: {e}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


@main_bp.route('/delete_history/<string:date_str>', methods=['DELETE'])
def delete_history_endpoint(date_str):
    """API endpoint to delete chat history for a specific date."""
    # Basic validation before calling DB function
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    try:
        deleted_count = delete_history_by_date(date_str)
        if deleted_count >= 0: # delete_history_by_date returns count or 0 on error/validation fail
            return jsonify({
                "success": True,
                "message": f"Deleted {deleted_count} entries for {date_str}.",
                "deleted_count": deleted_count
            }), 200
        else: # Should not happen with current db logic, but as safeguard
             return jsonify({"error": "Failed to delete history."}), 500
    except Exception as e:
        # Catch unexpected errors during deletion
        print(f"Error in /delete_history endpoint for {date_str}: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
