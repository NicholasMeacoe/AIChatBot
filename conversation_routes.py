from flask import Blueprint, jsonify, request
import sqlite3
from database import get_db

conversation_bp = Blueprint('conversations', __name__)

@conversation_bp.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation and its associated history."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # First delete all history entries for this conversation
        cursor.execute("DELETE FROM history WHERE conversation_id = ?", (conversation_id,))
        
        # Then delete the conversation itself
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        # Commit the changes
        conn.commit()
        
        # Check if any rows were affected
        if cursor.rowcount > 0:
            return jsonify({
                "success": True,
                "message": f"Conversation {conversation_id} deleted successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Conversation {conversation_id} not found"
            }), 404
            
    except sqlite3.Error as e:
        return jsonify({
            "success": False,
            "message": f"Database error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
