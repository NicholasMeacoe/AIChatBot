"""
Server-side fixes for chat endpoint issues
This file contains the corrected chat endpoint logic
"""

from flask import request, Response, jsonify
import json
import google.generativeai as genai
from database import get_db
import sqlite3

def fixed_chat_endpoint():
    """Fixed version of the chat endpoint with proper error handling and validation"""
    
    # Validate API key
    if not API_KEY:
        return Response(
            json.dumps({"error": "Gemini API Key not configured."}), 
            status=500, 
            mimetype='application/json'
        )
    
    # Validate request data
    try:
        data = request.json
        if not data:
            return Response(
                json.dumps({"error": "No JSON data provided"}), 
                status=400, 
                mimetype='application/json'
            )
    except Exception as e:
        return Response(
            json.dumps({"error": f"Invalid JSON data: {str(e)}"}), 
            status=400, 
            mimetype='application/json'
        )
    
    # Extract and validate required fields
    user_message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')
    selected_model_name = data.get('model_name', DEFAULT_MODEL_NAME)
    active_context_items = data.get('active_context', [])
    
    # Validate message
    if not user_message:
        return Response(
            json.dumps({"error": "Message cannot be empty"}), 
            status=400, 
            mimetype='application/json'
        )
    
    # Validate conversation ID
    if not conversation_id:
        return Response(
            json.dumps({"error": "Conversation ID is required"}), 
            status=400, 
            mimetype='application/json'
        )
    
    # Validate model selection
    if selected_model_name not in FETCHED_MODELS:
        print(f"Invalid model selected: {selected_model_name}")
        # Try to refresh model list
        try:
            global FETCHED_MODELS
            FETCHED_MODELS = get_available_models(API_KEY)
            if selected_model_name not in FETCHED_MODELS:
                return Response(
                    json.dumps({"error": f"Invalid model selected: {selected_model_name}"}), 
                    status=400, 
                    mimetype='application/json'
                )
        except Exception as e:
            print(f"Error refreshing model list: {e}")
            return Response(
                json.dumps({"error": "Failed to validate model selection"}), 
                status=500, 
                mimetype='application/json'
            )
    
    # Verify conversation exists
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, system_prompt, model FROM conversations WHERE id = ?", (conversation_id,))
        conversation = cursor.fetchone()
        conn.close()
        
        if not conversation:
            return Response(
                json.dumps({"error": f"Conversation {conversation_id} not found"}), 
                status=404, 
                mimetype='application/json'
            )
            
        system_prompt = conversation['system_prompt'] or ""
        stored_model = conversation['model'] or DEFAULT_MODEL_NAME
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return Response(
            json.dumps({"error": "Database error occurred"}), 
            status=500, 
            mimetype='application/json'
        )
    
    # Process context if provided
    context_errors = []
    processed_context = ""
    
    if active_context_items:
        try:
            # Process context items (simplified version)
            for item in active_context_items:
                if isinstance(item, dict) and 'path' in item:
                    # This would normally process files/URLs
                    # For now, just acknowledge the context
                    processed_context += f"[Context: {item['path']}]\n"
        except Exception as e:
            context_errors.append(f"Error processing context: {str(e)}")
    
    # Prepare final prompt
    final_prompt = ""
    if system_prompt:
        final_prompt += f"System: {system_prompt}\n\n"
    if processed_context:
        final_prompt += f"{processed_context}\n"
    final_prompt += f"User: {user_message}"
    
    # Initialize Gemini model
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(selected_model_name)
        print(f"Using Gemini model '{selected_model_name}' for conversation {conversation_id}")
    except Exception as e:
        print(f"Error initializing Gemini model: {e}")
        return Response(
            json.dumps({"error": f"Error initializing model: {str(e)}"}), 
            status=500, 
            mimetype='application/json'
        )
    
    # Generate streaming response
    def generate_response():
        full_bot_response = ""
        
        try:
            # Send context errors first if any
            if context_errors:
                for error in context_errors:
                    yield f"data: {json.dumps({'context_error': error})}\n\n"
            
            # Generate content with streaming
            try:
                stream = model.generate_content(final_prompt, stream=True)
                
                for chunk in stream:
                    if chunk.text:
                        full_bot_response += chunk.text
                        # Send chunk to client
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"
                        
            except Exception as e:
                print(f"Error during content generation: {e}")
                yield f"data: {json.dumps({'error': f'Generation error: {str(e)'})}\n\n"
                return
            
            # Save to database
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO history (conversation_id, user_message, bot_response, context_info) VALUES (?, ?, ?, ?)",
                    (conversation_id, user_message, full_bot_response, json.dumps(active_context_items) if active_context_items else None)
                )
                conn.commit()
                conn.close()
                print(f"Saved interaction to conversation {conversation_id}")
                
            except sqlite3.Error as e:
                print(f"Error saving to database: {e}")
                yield f"data: {json.dumps({'error': 'Failed to save conversation'})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'end_stream': True})}\n\n"
            
        except Exception as e:
            print(f"Unexpected error in generate_response: {e}")
            yield f"data: {json.dumps({'error': f'Unexpected error: {str(e)'})}\n\n"
    
    # Return streaming response
    return Response(
        generate_response(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST'
        }
    )

# Additional helper functions for the chat endpoint

def validate_conversation_exists(conversation_id):
    """Validate that a conversation exists in the database"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except sqlite3.Error:
        return False

def get_conversation_context(conversation_id, limit=10):
    """Get recent conversation history for context"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_message, bot_response FROM history WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT ?",
            (conversation_id, limit)
        )
        history = cursor.fetchall()
        conn.close()
        return list(reversed(history))  # Return in chronological order
    except sqlite3.Error as e:
        print(f"Error getting conversation context: {e}")
        return []

def sanitize_message(message):
    """Sanitize user message to prevent issues"""
    if not isinstance(message, str):
        return ""
    
    # Remove excessive whitespace
    message = ' '.join(message.split())
    
    # Limit message length
    if len(message) > 10000:
        message = message[:10000] + "... [truncated]"
    
    return message
