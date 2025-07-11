import google.generativeai as genai
from typing import Optional
import requests
import json
from config import GOOGLE_API_KEY, DEFAULT_MODEL_NAME

# Global variable to cache fetched models
FETCHED_MODELS_CACHE = []

def configure_client():
    """Configures the Google Generative AI SDK with the API key."""
    if not GOOGLE_API_KEY:
        print("Warning: GOOGLE_API_KEY not found. Some features may not work.")
        return False
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        return True
    except Exception as e:
        print(f"Error configuring Google AI: {e}")
        return False

def get_available_models():
    """Fetches available models from the Google Generative AI API."""
    global FETCHED_MODELS_CACHE
    
    if FETCHED_MODELS_CACHE:
        return FETCHED_MODELS_CACHE
    
    if not configure_client():
        return [DEFAULT_MODEL_NAME]
    
    try:
        models = genai.list_models()
        model_names = []
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                model_names.append(model.name)
        
        FETCHED_MODELS_CACHE = model_names if model_names else [DEFAULT_MODEL_NAME]
        return FETCHED_MODELS_CACHE
        
    except Exception as e:
        print(f"Error fetching models: {e}")
        return [DEFAULT_MODEL_NAME]

def generate_response_stream(prompt, model_name=None):
    """Generate streaming response from Gemini model."""
    if not configure_client():
        yield "Error: Google AI not configured properly"
        return
    
    try:
        model_name = model_name or DEFAULT_MODEL_NAME
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(prompt, stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text
                
    except Exception as e:
        yield f"Error generating response: {str(e)}"

def generate_response(prompt, model_name=None):
    """Generate non-streaming response from Gemini model."""
    if not configure_client():
        return "Error: Google AI not configured properly"
    
    try:
        model_name = model_name or DEFAULT_MODEL_NAME
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generating response: {str(e)}"

def generate_summary(content, max_length=200):
    """Generate a summary of the given content."""
    if not configure_client():
        return "Error: Google AI not configured properly"
    
    try:
        prompt = f"Please provide a concise summary of the following content in no more than {max_length} characters:\n\n{content}"
        model = genai.GenerativeModel(DEFAULT_MODEL_NAME)
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"
