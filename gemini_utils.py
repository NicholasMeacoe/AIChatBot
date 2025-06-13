from google import genai
from google.genai import models, types
from typing import Optional
import requests
import json
from config import GOOGLE_API_KEY, DEFAULT_MODEL_NAME

# Global variable to cache fetched models
FETCHED_MODELS_CACHE = []
client: genai.Client = None

def configure_client():
    """Configures the Google Generative AI SDK with the API key."""
    global client
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY not found. Gemini API cannot be configured.")
        return False
    try:
        # The core of the configuration is creating the genai.Client instance.
        # The mock_gemini_client fixture in conftest.py patches 'gemini_utils.genai.Client'
        # so this call will use the mock during tests that use that fixture.
        client = genai.Client(api_key=GOOGLE_API_KEY)
        print("Gemini client configured successfully using API Key.") # Simplified message
        return True
    except Exception as e:
        print(f"Error configuring Gemini client: {e}")
        return False

def get_available_models(force_refresh=False):
    """
    Fetches available models from the Google Generative Language API.
    Uses a cache unless force_refresh is True.
    Returns a list of model names (e.g., 'gemini-1.5-flash-latest').
    """
    global FETCHED_MODELS_CACHE
    if FETCHED_MODELS_CACHE and not force_refresh:
        print("Using cached model list.")
        return FETCHED_MODELS_CACHE

    if not GOOGLE_API_KEY:
        print("Warning: Cannot fetch models, API key is missing. Returning default.")
        FETCHED_MODELS_CACHE = [DEFAULT_MODEL_NAME]
        return FETCHED_MODELS_CACHE

    models_list = []
    try:
        # Note: The Python SDK `genai.list_models()` might be simpler if it provides
        # the necessary filtering capabilities. Let's try the SDK first.
        print("Fetching available models via SDK...")
        sdk_models = client.models.list()
        for m in sdk_models:
            # Filter for models supporting 'generateContent' (standard for chat/text)
            if 'generateContent' in m.supported_actions:
                 # Extract the model name after 'models/'
                 model_name = m.name.split('/')[-1]
                 # Optional: Further filter if needed (e.g., only 'gemini-' models)
                 if model_name.startswith('gemini'):
                    models_list.append(model_name)

        if not models_list:
            print("Warning: No suitable models found via SDK. Falling back to default.")
            models_list = [DEFAULT_MODEL_NAME]
        else:
            print(f"Fetched available models via SDK: {models_list}")
            models_list = sorted(models_list) # Sort for consistency

    except Exception as e_sdk:
        print(f"Error fetching models via SDK: {e_sdk}. Trying direct API call...")
        # Fallback to direct API call if SDK fails or doesn't work as expected
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            for model_info in data.get('models', []):
                supported_methods = model_info.get('supportedGenerationMethods', [])
                if 'generateContent' in supported_methods:
                    model_name_full = model_info.get('name')
                    if model_name_full and model_name_full.startswith('models/gemini'):
                        model_name = model_name_full.split('/')[-1]
                        if model_name not in models_list: # Avoid duplicates if SDK partially worked
                             models_list.append(model_name)

            if not models_list:
                print("Warning: No suitable models found via direct API call either. Falling back to default.")
                models_list = [DEFAULT_MODEL_NAME]
            else:
                 print(f"Fetched available models via direct API: {models_list}")
                 models_list = sorted(models_list)

        except requests.exceptions.RequestException as e_api:
            print(f"Error fetching models from direct API: {e_api}. Falling back to default.")
            models_list = [DEFAULT_MODEL_NAME]
        except Exception as e_generic:
            print(f"Unexpected error fetching models: {e_generic}. Falling back to default.")
            models_list = [DEFAULT_MODEL_NAME]

    # Ensure the default model is always in the list
    if DEFAULT_MODEL_NAME not in models_list:
        models_list.insert(0, DEFAULT_MODEL_NAME) # Add default at the beginning if missing

    FETCHED_MODELS_CACHE = models_list
    return FETCHED_MODELS_CACHE

def generate_response_stream(prompt, model_name=DEFAULT_MODEL_NAME):
    """
    Generates a response from the Gemini model using streaming.
    Yields JSON strings for SSE (Server-Sent Events).
    """
    try:
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=prompt
        ):
            if chunk.text:
                # Send chunk to client via SSE
                data = json.dumps({"text": chunk.text})
                yield f"data: {data}\n\n" # SSE format

        # Signal end of stream
        yield f"data: {json.dumps({'end_stream': True})}\n\n"

    except ValueError as ve: # Catch configuration/model instantiation errors
         error_data = json.dumps({"error": f"Model configuration error: {ve}"})
         yield f"data: {error_data}\n\n"
    except Exception as e:
        print(f"Error during Gemini generation: {e}")
        # Send error to client via SSE
        error_data = json.dumps({"error": f"An error occurred during generation: {e}"})
        yield f"data: {error_data}\n\n"

def generate_summary(prompt, model_name=DEFAULT_MODEL_NAME):
    """Generates a non-streaming response, suitable for summarization."""
    try:
        response = client.models.generate_content(model_name, prompt) # Non-streaming call
        return response.text
    except ValueError as ve:
        print(f"Model configuration error during summary: {ve}")
        raise # Re-raise to be handled by the route
    except Exception as e:
        print(f"Error during Gemini summary generation: {e}")
        raise # Re-raise to be handled by the route

# Example usage (optional, for testing the module directly)
if __name__ == '__main__':
    if configure_client(): # Renamed
        models = get_available_models(force_refresh=True)
        print("\nAvailable Models:")
        print(models)

        if models:
            print(f"\nAttempting to instantiate default model: {DEFAULT_MODEL_NAME}")
            try:
                model = client.models.get(model=DEFAULT_MODEL_NAME)
                print(model)
            except Exception as e:
                 print(f"Failed: {e}")

            # Test streaming (simple prompt)
            # print("\nTesting streaming generation...")
            # test_prompt = "Explain the concept of a large language model in one sentence."
            # for chunk_data in generate_response_stream(test_prompt, DEFAULT_MODEL_NAME):
            #     print(chunk_data, end='')

            # Test summary (simple prompt)
            # print("\nTesting summary generation...")
            # try:
            #     summary = generate_summary(test_prompt, DEFAULT_MODEL_NAME)
            #     print(f"Summary: {summary}")
            # except Exception as e:
            #     print(f"Summary failed: {e}")
