"""
OAuth2 Authentication Implementation
"""
import json
import requests
from flask import current_app, url_for, session, redirect, request
from authlib.integrations.flask_client import OAuth
from auth_config import AuthConfig
from user_management import UserManager

class OAuth2Manager:
    """Manages OAuth2 authentication flow"""
    
    def __init__(self, app=None):
        self.oauth = OAuth()
        self.user_manager = UserManager()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize OAuth2 with Flask app"""
        self.oauth.init_app(app)
        
        # Validate configuration
        try:
            AuthConfig.validate_config()
        except ValueError as e:
            current_app.logger.error(f"OAuth2 configuration error: {e}")
            return False
        
        # Register OAuth2 provider
        self._register_provider()
        return True
    
    def _register_provider(self):
        """Register OAuth2 provider based on configuration"""
        provider = AuthConfig.OAUTH2_PROVIDER
        config = AuthConfig.get_oauth_config()
        
        if provider == 'google':
            self.client = self.oauth.register(
                name='google',
                client_id=config['client_id'],
                client_secret=config['client_secret'],
                server_metadata_url=config['discovery_url'],
                client_kwargs={
                    'scope': ' '.join(config['scopes'])
                }
            )
        
        elif provider == 'github':
            self.client = self.oauth.register(
                name='github',
                client_id=config['client_id'],
                client_secret=config['client_secret'],
                access_token_url=config['token_url'],
                authorize_url=config['authorization_url'],
                api_base_url='https://api.github.com/',
                client_kwargs={'scope': ' '.join(config['scopes'])}
            )
        
        elif provider == 'custom':
            self.client = self.oauth.register(
                name='custom',
                client_id=config['client_id'],
                client_secret=config['client_secret'],
                access_token_url=config['token_url'],
                authorize_url=config['authorization_url'],
                api_base_url=config['userinfo_url'],
                client_kwargs={'scope': ' '.join(config['scopes'])}
            )
    
    def get_authorization_url(self):
        """Get OAuth2 authorization URL"""
        redirect_uri = url_for('auth.callback', _external=True)
        return self.client.authorize_redirect(redirect_uri)
    
    def handle_callback(self):
        """Handle OAuth2 callback"""
        try:
            # Get access token
            token = self.client.authorize_access_token()
            
            # Get user info
            user_info = self._get_user_info(token)
            
            if not user_info:
                return None, "Failed to get user information"
            
            # Create or update user
            user = self.user_manager.create_or_update_user(
                user_id=user_info['id'],
                email=user_info['email'],
                name=user_info['name']
            )
            
            return user, None
            
        except Exception as e:
            current_app.logger.error(f"OAuth2 callback error: {e}")
            return None, str(e)
    
    def _get_user_info(self, token):
        """Get user information from OAuth2 provider"""
        provider = AuthConfig.OAUTH2_PROVIDER
        
        try:
            if provider == 'google':
                resp = self.client.parse_id_token(token)
                return {
                    'id': resp['sub'],
                    'email': resp['email'],
                    'name': resp['name']
                }
            
            elif provider == 'github':
                # Get user info
                resp = self.client.get('user', token=token)
                user_data = resp.json()
                
                # Get user email (GitHub might not provide email in user endpoint)
                email_resp = self.client.get('user/emails', token=token)
                emails = email_resp.json()
                primary_email = next((email['email'] for email in emails if email['primary']), None)
                
                return {
                    'id': str(user_data['id']),
                    'email': primary_email or user_data.get('email'),
                    'name': user_data.get('name') or user_data.get('login')
                }
            
            elif provider == 'custom':
                # For custom providers, make a request to userinfo endpoint
                config = AuthConfig.get_oauth_config()
                headers = {'Authorization': f"Bearer {token['access_token']}"}
                resp = requests.get(config['userinfo_url'], headers=headers)
                
                if resp.status_code == 200:
                    user_data = resp.json()
                    return {
                        'id': user_data.get('sub') or user_data.get('id'),
                        'email': user_data.get('email'),
                        'name': user_data.get('name') or user_data.get('preferred_username')
                    }
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error getting user info: {e}")
            return None
    
    def logout_user(self):
        """Logout user and clear session"""
        session.clear()
        return True

# Decorators for route protection
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def feature_required(feature_name):
    """Decorator to require specific feature access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not current_user.can_access_feature(feature_name):
                flash('You do not have permission to access this feature.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit_check(f):
    """Decorator to check rate limits"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return f(*args, **kwargs)
        
        if not current_user.can_make_request():
            flash('Rate limit exceeded. Please try again later.', 'warning')
            return redirect(url_for('main.index'))
        
        # Increment request count
        user_manager = UserManager()
        user_manager.increment_request_count(current_user.id)
        
        return f(*args, **kwargs)
    return decorated_function
