from google import genai # Corrected import
from google.genai import types # types is still used for things like SafetySetting
from typing import Optional
import requests
import json
from config import GOOGLE_API_KEY, DEFAULT_MODEL_NAME

# Global variable to cache fetched models
FETCHED_MODELS_CACHE = []
# client will be initialized by configure_client
client: Optional[genai.client.Client] = None # Use full path for clarity if needed

def configure_client():
    """Configures the Google Generative AI SDK with the API key."""
    global client
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY not found. Gemini API cannot be configured.")
        # In the new SDK, client isn't configured globally first,
        # but we maintain this structure for now.
        client = None
        return False
    try:
        # Initialize the client. API key is picked up from env var if not passed.
        # For explicit key: client = genai.Client(api_key=GOOGLE_API_KEY)
        client = genai.Client()
        print("Gemini client configured successfully.")
        return True
    except Exception as e:
        print(f"Error configuring Gemini client: {e}")
        client = None
        return False

def get_available_models(force_refresh=False):
    """
    Fetches available models from the Google Generative Language API.
    Uses a cache unless force_refresh is True.
    Returns a list of model names (e.g., 'models/gemini-1.5-flash-latest').
    The new SDK returns model names with "models/" prefix.
    """
    global FETCHED_MODELS_CACHE, client
    if not client:
        print("Warning: Gemini client not configured. Cannot fetch models.")
        return [DEFAULT_MODEL_NAME] # Return default if client is not setup

    if FETCHED_MODELS_CACHE and not force_refresh:
        print("Using cached model list.")
        return FETCHED_MODELS_CACHE

    models_list = []
    try:
        print("Fetching available models via new SDK...")
        sdk_models_raw = []
        for m in client.models.list():
            # Filter for models supporting 'generateContent' (standard for chat/text)
            # and ensure it's a Gemini model. The name format is now 'models/model-name'
            if 'generateContent' in m.supported_actions and hasattr(m, 'name') and m.name.startswith('models/gemini'):
                sdk_models_raw.append(m.name) # Store the full name string

        if not sdk_models_raw:
            print("Warning: No suitable 'gemini' models found via SDK. Falling back to default.")
            models_list = [DEFAULT_MODEL_NAME] # DEFAULT_MODEL_NAME should be prefixed
        else:
            # Sort the collected model name strings
            models_list = sorted(list(set(sdk_models_raw))) # Ensure uniqueness and sort
            print(f"Fetched and sorted available models via new SDK: {models_list}")

    except Exception as e_sdk:
        print(f"Error fetching models via new SDK: {e_sdk}. Falling back to default.")
        models_list = [DEFAULT_MODEL_NAME] # DEFAULT_MODEL_NAME should be prefixed

    # Ensure the default model is always in the list.
    # DEFAULT_MODEL_NAME from config.py is now expected to be prefixed, e.g., "models/gemini-1.5-flash-latest"
    if DEFAULT_MODEL_NAME not in models_list:
        models_list.append(DEFAULT_MODEL_NAME)
        models_list = sorted(list(set(models_list))) # Re-sort and ensure uniqueness

    FETCHED_MODELS_CACHE = models_list
    return FETCHED_MODELS_CACHE


def generate_response_stream(prompt, model_name=DEFAULT_MODEL_NAME):
    """
    Generates a response from the Gemini model using streaming.
    Yields JSON strings for SSE (Server-Sent Events).
    Model name should be the full name, e.g., 'models/gemini-1.5-flash-latest'.
    """
    global client
    if not client:
        error_data = json.dumps({"error": "Gemini client not configured."})
        yield f"data: {error_data}\n\n"
        return

    # Ensure model_name has "models/" prefix if not already present
    if not model_name.startswith("models/"):
        model_name = f"models/{model_name}"

    try:
        # The new SDK uses client.models.generate_content for streaming as well
        stream = client.models.generate_content(
            model=model_name,
            contents=prompt,
            stream=True
        )
        for chunk in stream:
            if chunk.text:
                data = json.dumps({"text": chunk.text})
                yield f"data: {data}\n\n"

        yield f"data: {json.dumps({'end_stream': True})}\n\n"

    except Exception as e: # Catch more general exceptions from the SDK
        print(f"Error during Gemini generation (new SDK): {e}")
        error_data = json.dumps({"error": f"An error occurred during generation: {str(e)}"})
        yield f"data: {error_data}\n\n"

def generate_summary(prompt, model_name=DEFAULT_MODEL_NAME):
    """
    Generates a non-streaming response, suitable for summarization.
    Model name should be the full name, e.g., 'models/gemini-1.5-flash-latest'.
    """
    global client
    if not client:
        raise ValueError("Gemini client not configured.")

    if not model_name.startswith("models/"):
        model_name = f"models/{model_name}"

    try:
        # Non-streaming call in the new SDK
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e: # Catch more general exceptions
        print(f"Error during Gemini summary generation (new SDK): {e}")
        raise # Re-raise to be handled by the route

# Example usage (optional, for testing the module directly)
if __name__ == '__main__':
    if configure_client():
        models = get_available_models(force_refresh=True)
        print("\nAvailable Models (new SDK):")
        print(models)

        if models:
            # The default model name might need "models/" prefix
            current_default_model_for_test = DEFAULT_MODEL_NAME
            if not current_default_model_for_test.startswith("models/"):
                 current_default_model_for_test = f"models/{current_default_model_for_test}"

            if current_default_model_for_test not in models:
                print(f"\nWarning: Default model {current_default_model_for_test} not in fetched list. Using first available model for tests if any.")
                current_default_model_for_test = models[0] if models else None

            if current_default_model_for_test:
                print(f"\nAttempting to use model for tests: {current_default_model_for_test}")
                # client.models.get() is not the primary way to check in new SDK,
                # but listing and then using one is fine.
                # We can try a simple generation.

                # Test streaming (simple prompt)
                print("\nTesting streaming generation (new SDK)...")
                test_prompt_stream = "Explain the concept of a large language model in one sentence."
                try:
                    for chunk_data in generate_response_stream(test_prompt_stream, current_default_model_for_test):
                        print(chunk_data, end='')
                except Exception as e_stream:
                    print(f"Streaming test failed: {e_stream}")

                # Test summary (simple prompt)
                print("\nTesting summary generation (new SDK)...")
                test_prompt_summary = "Summarize the importance of AI ethics."
                try:
                    summary = generate_summary(test_prompt_summary, current_default_model_for_test)
                    print(f"Summary: {summary}")
                except Exception as e_summary:
                    print(f"Summary test failed: {e_summary}")
            else:
                print("\nNo models available to test.")
    else:
        print("Failed to configure client for __main__ test.")
