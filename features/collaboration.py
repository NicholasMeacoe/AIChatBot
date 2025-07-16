import json
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room

class CollaborationManager:
    def __init__(self, socketio):
        self.socketio = socketio
        self.active_sessions = {}
        self.user_presence = {}
        
        # Socket event handlers
        @socketio.on('join_session')
        def handle_join_session(data):
            session_id = data['session_id']
            user_id = data['user_id']
            username = data.get('username', f'User_{user_id[:8]}')
            
            join_room(session_id)
            
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = {'users': {}, 'context': []}
            
            self.active_sessions[session_id]['users'][user_id] = {
                'username': username,
                'joined_at': datetime.now().isoformat()
            }
            
            emit('user_joined', {
                'user_id': user_id,
                'username': username,
                'users': self.active_sessions[session_id]['users']
            }, room=session_id)
        
        @socketio.on('leave_session')
        def handle_leave_session(data):
            session_id = data['session_id']
            user_id = data['user_id']
            
            leave_room(session_id)
            
            if session_id in self.active_sessions:
                self.active_sessions[session_id]['users'].pop(user_id, None)
                
                emit('user_left', {
                    'user_id': user_id,
                    'users': self.active_sessions[session_id]['users']
                }, room=session_id)
        
        @socketio.on('message_sent')
        def handle_message_sent(data):
            session_id = data['session_id']
            message = data['message']
            user_id = data['user_id']
            
            emit('new_message', {
                'message': message,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }, room=session_id, include_self=False)
        
        @socketio.on('context_updated')
        def handle_context_updated(data):
            session_id = data['session_id']
            context_items = data['context_items']
            user_id = data['user_id']
            
            if session_id in self.active_sessions:
                self.active_sessions[session_id]['context'] = context_items
            
            emit('context_changed', {
                'context_items': context_items,
                'updated_by': user_id,
                'timestamp': datetime.now().isoformat()
            }, room=session_id, include_self=False)
    
    def get_session_info(self, session_id):
        """Get current session information"""
        return self.active_sessions.get(session_id, {'users': {}, 'context': []})