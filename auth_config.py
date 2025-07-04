"""
OAuth2 Authentication Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

class AuthConfig:
    """OAuth2 configuration settings"""
    
    # OAuth2 Provider Settings
    OAUTH2_PROVIDER = os.getenv('OAUTH2_PROVIDER', 'google')  # google, github, custom
    
    # Google OAuth2 Settings
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid_configuration"
    
    # GitHub OAuth2 Settings
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
    
    # Custom OAuth2 Settings
    CUSTOM_CLIENT_ID = os.getenv('CUSTOM_CLIENT_ID')
    CUSTOM_CLIENT_SECRET = os.getenv('CUSTOM_CLIENT_SECRET')
    CUSTOM_AUTHORIZATION_URL = os.getenv('CUSTOM_AUTHORIZATION_URL')
    CUSTOM_TOKEN_URL = os.getenv('CUSTOM_TOKEN_URL')
    CUSTOM_USERINFO_URL = os.getenv('CUSTOM_USERINFO_URL')
    
    # Application Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Authorization Settings
    ENABLE_ROLE_BASED_ACCESS = os.getenv('ENABLE_ROLE_BASED_ACCESS', 'true').lower() == 'true'
    DEFAULT_USER_ROLE = os.getenv('DEFAULT_USER_ROLE', 'user')
    ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',') if os.getenv('ADMIN_EMAILS') else []
    
    # Rate Limiting
    ENABLE_RATE_LIMITING = os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    RATE_LIMIT_PER_USER = int(os.getenv('RATE_LIMIT_PER_USER', '100'))  # requests per hour
    
    @classmethod
    def get_oauth_config(cls):
        """Get OAuth configuration based on provider"""
        if cls.OAUTH2_PROVIDER == 'google':
            return {
                'client_id': cls.GOOGLE_CLIENT_ID,
                'client_secret': cls.GOOGLE_CLIENT_SECRET,
                'discovery_url': cls.GOOGLE_DISCOVERY_URL,
                'scopes': ['openid', 'email', 'profile']
            }
        elif cls.OAUTH2_PROVIDER == 'github':
            return {
                'client_id': cls.GITHUB_CLIENT_ID,
                'client_secret': cls.GITHUB_CLIENT_SECRET,
                'authorization_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token',
                'userinfo_url': 'https://api.github.com/user',
                'scopes': ['user:email']
            }
        elif cls.OAUTH2_PROVIDER == 'custom':
            return {
                'client_id': cls.CUSTOM_CLIENT_ID,
                'client_secret': cls.CUSTOM_CLIENT_SECRET,
                'authorization_url': cls.CUSTOM_AUTHORIZATION_URL,
                'token_url': cls.CUSTOM_TOKEN_URL,
                'userinfo_url': cls.CUSTOM_USERINFO_URL,
                'scopes': ['openid', 'email', 'profile']
            }
        else:
            raise ValueError(f"Unsupported OAuth2 provider: {cls.OAUTH2_PROVIDER}")
    
    @classmethod
    def validate_config(cls):
        """Validate OAuth configuration"""
        config = cls.get_oauth_config()
        missing_keys = [key for key, value in config.items() if not value and key != 'scopes']
        
        if missing_keys:
            raise ValueError(f"Missing OAuth2 configuration: {', '.join(missing_keys)}")
        
        return True
