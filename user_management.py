"""
User Management and Database Operations
"""
import sqlite3
import json
from datetime import datetime, timedelta
from flask_login import UserMixin
from auth_config import AuthConfig

class User(UserMixin):
    """User model for Flask-Login"""
    
    def __init__(self, user_id, email, name, role='user', created_at=None, last_login=None, 
                 request_count=0, is_active=True):
        self.id = user_id
        self.email = email
        self.name = name
        self.role = role
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        self.request_count = request_count
        self.is_active = is_active
    
    def get_id(self):
        return str(self.id)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def can_access_feature(self, feature):
        """Check if user can access a specific feature"""
        if not AuthConfig.ENABLE_ROLE_BASED_ACCESS:
            return True
            
        feature_permissions = {
            'chat': ['user', 'admin'],
            'history_view': ['user', 'admin'],
            'history_delete': ['admin'],
            'context_management': ['user', 'admin'],
            'pdf_conversion': ['user', 'admin'],
            'admin_panel': ['admin']
        }
        
        return self.role in feature_permissions.get(feature, [])
    
    def can_make_request(self):
        """Check if user can make a request based on rate limiting"""
        if not AuthConfig.ENABLE_RATE_LIMITING:
            return True
            
        # Check if user has exceeded rate limit
        return self.request_count < AuthConfig.RATE_LIMIT_PER_USER
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'request_count': self.request_count,
            'is_active': self.is_active
        }

class UserManager:
    """Manages user operations and database interactions"""
    
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize user database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    request_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # User sessions table for rate limiting
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id TEXT,
                    session_start TIMESTAMP,
                    request_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # User chat history permissions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_chat_permissions (
                    user_id TEXT,
                    chat_id INTEGER,
                    permission TEXT DEFAULT 'read',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def create_or_update_user(self, user_id, email, name):
        """Create a new user or update existing user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            existing_user = cursor.fetchone()
            
            # Determine role
            role = 'admin' if email in AuthConfig.ADMIN_EMAILS else AuthConfig.DEFAULT_USER_ROLE
            
            if existing_user:
                # Update existing user
                cursor.execute('''
                    UPDATE users 
                    SET email = ?, name = ?, role = ?, last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (email, name, role, user_id))
            else:
                # Create new user
                cursor.execute('''
                    INSERT INTO users (id, email, name, role, created_at, last_login)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, email, name, role))
            
            conn.commit()
            
            # Return user object
            return self.get_user(user_id)
    
    def get_user(self, user_id):
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                return User(
                    user_id=row[0],
                    email=row[1],
                    name=row[2],
                    role=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    last_login=datetime.fromisoformat(row[5]) if row[5] else None,
                    request_count=row[6],
                    is_active=bool(row[7])
                )
            return None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            
            if row:
                return User(
                    user_id=row[0],
                    email=row[1],
                    name=row[2],
                    role=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    last_login=datetime.fromisoformat(row[5]) if row[5] else None,
                    request_count=row[6],
                    is_active=bool(row[7])
                )
            return None
    
    def increment_request_count(self, user_id):
        """Increment user's request count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET request_count = request_count + 1 
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
    
    def reset_request_counts(self):
        """Reset all users' request counts (called hourly)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET request_count = 0')
            conn.commit()
    
    def get_all_users(self):
        """Get all users (admin function)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            users = []
            for row in rows:
                users.append(User(
                    user_id=row[0],
                    email=row[1],
                    name=row[2],
                    role=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    last_login=datetime.fromisoformat(row[5]) if row[5] else None,
                    request_count=row[6],
                    is_active=bool(row[7])
                ))
            
            return users
    
    def update_user_role(self, user_id, new_role):
        """Update user role (admin function)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            conn.commit()
    
    def deactivate_user(self, user_id):
        """Deactivate user (admin function)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
            conn.commit()
