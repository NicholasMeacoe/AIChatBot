"""
Tests for OAuth2 Authentication Implementation
"""
import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_login import LoginManager

# Import our OAuth2 components
from auth_config import AuthConfig
from user_management import User, UserManager
from oauth_auth import OAuth2Manager
from auth_routes import auth_bp

class TestAuthConfig:
    """Test OAuth2 configuration management"""
    
    def setup_method(self):
        """Setup test environment"""
        self.original_env = os.environ.copy()
    
    def teardown_method(self):
        """Cleanup test environment"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_google_oauth_config(self):
        """Test Google OAuth2 configuration"""
        os.environ.update({
            'OAUTH2_PROVIDER': 'google',
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        })
        
        config = AuthConfig.get_oauth_config()
        
        assert config['client_id'] == 'test_client_id'
        assert config['client_secret'] == 'test_client_secret'
        assert 'openid' in config['scopes']
        assert 'email' in config['scopes']
    
    def test_github_oauth_config(self):
        """Test GitHub OAuth2 configuration"""
        os.environ.update({
            'OAUTH2_PROVIDER': 'github',
            'GITHUB_CLIENT_ID': 'test_github_id',
            'GITHUB_CLIENT_SECRET': 'test_github_secret'
        })
        
        config = AuthConfig.get_oauth_config()
        
        assert config['client_id'] == 'test_github_id'
        assert config['client_secret'] == 'test_github_secret'
        assert 'user:email' in config['scopes']
    
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        os.environ.update({
            'OAUTH2_PROVIDER': 'google',
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        })
        
        assert AuthConfig.validate_config() == True
    
    def test_config_validation_failure(self):
        """Test configuration validation failure"""
        os.environ.update({
            'OAUTH2_PROVIDER': 'google',
            'GOOGLE_CLIENT_ID': '',  # Missing client ID
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        })
        
        with pytest.raises(ValueError):
            AuthConfig.validate_config()

class TestUser:
    """Test User model"""
    
    def test_user_creation(self):
        """Test user object creation"""
        user = User(
            user_id='test_123',
            email='test@example.com',
            name='Test User',
            role='user'
        )
        
        assert user.id == 'test_123'
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
        assert user.role == 'user'
        assert user.is_active == True
    
    def test_user_permissions(self):
        """Test user permission checking"""
        # Regular user
        user = User('test_123', 'test@example.com', 'Test User', 'user')
        
        assert user.can_access_feature('chat') == True
        assert user.can_access_feature('history_view') == True
        assert user.can_access_feature('history_delete') == False
        assert user.can_access_feature('admin_panel') == False
        
        # Admin user
        admin = User('admin_123', 'admin@example.com', 'Admin User', 'admin')
        
        assert admin.can_access_feature('chat') == True
        assert admin.can_access_feature('history_view') == True
        assert admin.can_access_feature('history_delete') == True
        assert admin.can_access_feature('admin_panel') == True
        assert admin.is_admin() == True
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        user = User('test_123', 'test@example.com', 'Test User', 'user', request_count=50)
        
        assert user.can_make_request() == True
        
        # Exceed rate limit
        user.request_count = 150
        assert user.can_make_request() == False
    
    def test_user_serialization(self):
        """Test user to dictionary conversion"""
        user = User('test_123', 'test@example.com', 'Test User', 'user')
        user_dict = user.to_dict()
        
        assert user_dict['id'] == 'test_123'
        assert user_dict['email'] == 'test@example.com'
        assert user_dict['name'] == 'Test User'
        assert user_dict['role'] == 'user'

class TestUserManager:
    """Test UserManager database operations"""
    
    def setup_method(self):
        """Setup test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.user_manager = UserManager(self.temp_db.name)
    
    def teardown_method(self):
        """Cleanup test database"""
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database table creation"""
        # Database should be initialized in setup
        assert os.path.exists(self.temp_db.name)
        
        # Test that we can create a user
        user = self.user_manager.create_or_update_user(
            'test_123', 'test@example.com', 'Test User'
        )
        assert user is not None
        assert user.id == 'test_123'
    
    def test_user_creation(self):
        """Test user creation and retrieval"""
        # Create user
        user = self.user_manager.create_or_update_user(
            'test_123', 'test@example.com', 'Test User'
        )
        
        assert user.id == 'test_123'
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
        assert user.role == 'user'  # Default role
        
        # Retrieve user
        retrieved_user = self.user_manager.get_user('test_123')
        assert retrieved_user is not None
        assert retrieved_user.id == 'test_123'
    
    def test_admin_user_creation(self):
        """Test admin user creation based on email"""
        # Mock admin emails
        with patch.object(AuthConfig, 'ADMIN_EMAILS', ['admin@example.com']):
            admin_user = self.user_manager.create_or_update_user(
                'admin_123', 'admin@example.com', 'Admin User'
            )
            
            assert admin_user.role == 'admin'
    
    def test_user_update(self):
        """Test user information update"""
        # Create user
        user = self.user_manager.create_or_update_user(
            'test_123', 'test@example.com', 'Test User'
        )
        
        # Update user
        updated_user = self.user_manager.create_or_update_user(
            'test_123', 'updated@example.com', 'Updated User'
        )
        
        assert updated_user.email == 'updated@example.com'
        assert updated_user.name == 'Updated User'
    
    def test_request_count_increment(self):
        """Test request count increment"""
        # Create user
        user = self.user_manager.create_or_update_user(
            'test_123', 'test@example.com', 'Test User'
        )
        
        initial_count = user.request_count
        
        # Increment request count
        self.user_manager.increment_request_count('test_123')
        
        # Retrieve updated user
        updated_user = self.user_manager.get_user('test_123')
        assert updated_user.request_count == initial_count + 1
    
    def test_get_all_users(self):
        """Test retrieving all users"""
        # Create multiple users
        self.user_manager.create_or_update_user('user1', 'user1@example.com', 'User 1')
        self.user_manager.create_or_update_user('user2', 'user2@example.com', 'User 2')
        
        users = self.user_manager.get_all_users()
        assert len(users) == 2
        
        user_ids = [user.id for user in users]
        assert 'user1' in user_ids
        assert 'user2' in user_ids
    
    def test_role_update(self):
        """Test user role update"""
        # Create user
        user = self.user_manager.create_or_update_user(
            'test_123', 'test@example.com', 'Test User'
        )
        assert user.role == 'user'
        
        # Update role
        self.user_manager.update_user_role('test_123', 'admin')
        
        # Verify role update
        updated_user = self.user_manager.get_user('test_123')
        assert updated_user.role == 'admin'
    
    def test_user_deactivation(self):
        """Test user deactivation"""
        # Create user
        user = self.user_manager.create_or_update_user(
            'test_123', 'test@example.com', 'Test User'
        )
        assert user.is_active == True
        
        # Deactivate user
        self.user_manager.deactivate_user('test_123')
        
        # Verify deactivation
        deactivated_user = self.user_manager.get_user('test_123')
        assert deactivated_user.is_active == False

class TestOAuth2Manager:
    """Test OAuth2Manager functionality"""
    
    def setup_method(self):
        """Setup test Flask app"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret_key'
        self.app.config['TESTING'] = True
        
        # Mock OAuth2 configuration
        with patch.object(AuthConfig, 'OAUTH2_PROVIDER', 'google'), \
             patch.object(AuthConfig, 'GOOGLE_CLIENT_ID', 'test_client_id'), \
             patch.object(AuthConfig, 'GOOGLE_CLIENT_SECRET', 'test_client_secret'):
            
            self.oauth_manager = OAuth2Manager(self.app)
    
    def test_oauth_manager_initialization(self):
        """Test OAuth2Manager initialization"""
        assert self.oauth_manager is not None
        assert hasattr(self.oauth_manager, 'oauth')
        assert hasattr(self.oauth_manager, 'user_manager')
    
    @patch('oauth_auth.OAuth2Manager._get_user_info')
    @patch('oauth_auth.OAuth2Manager.client')
    def test_callback_handling_success(self, mock_client, mock_get_user_info):
        """Test successful OAuth2 callback handling"""
        # Mock OAuth2 response
        mock_token = {'access_token': 'test_token'}
        mock_client.authorize_access_token.return_value = mock_token
        
        # Mock user info
        mock_get_user_info.return_value = {
            'id': 'test_123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        
        with self.app.app_context():
            user, error = self.oauth_manager.handle_callback()
            
            assert error is None
            assert user is not None
            assert user.email == 'test@example.com'
    
    @patch('oauth_auth.OAuth2Manager.client')
    def test_callback_handling_failure(self, mock_client):
        """Test OAuth2 callback handling failure"""
        # Mock OAuth2 error
        mock_client.authorize_access_token.side_effect = Exception('OAuth2 error')
        
        with self.app.app_context():
            user, error = self.oauth_manager.handle_callback()
            
            assert user is None
            assert error is not None
            assert 'OAuth2 error' in error

class TestAuthRoutes:
    """Test authentication routes"""
    
    def setup_method(self):
        """Setup test Flask app with auth routes"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret_key'
        self.app.config['TESTING'] = True
        
        # Initialize Flask-Login
        login_manager = LoginManager()
        login_manager.init_app(self.app)
        login_manager.login_view = 'auth.login'
        
        # Register auth blueprint
        self.app.register_blueprint(auth_bp)
        
        self.client = self.app.test_client()
    
    def test_login_page(self):
        """Test login page access"""
        response = self.client.get('/auth/login')
        assert response.status_code == 200
        assert b'Sign in to start chatting' in response.data
    
    def test_auth_status_unauthenticated(self):
        """Test authentication status for unauthenticated user"""
        response = self.client.get('/auth/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['authenticated'] == False
    
    def test_logout_redirect(self):
        """Test logout redirect for unauthenticated user"""
        response = self.client.get('/auth/logout')
        # Should redirect to login page
        assert response.status_code == 302

class TestIntegration:
    """Integration tests for OAuth2 system"""
    
    def setup_method(self):
        """Setup complete test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        # Setup Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret_key'
        self.app.config['TESTING'] = True
        
        # Mock environment variables
        self.env_patch = patch.dict(os.environ, {
            'OAUTH2_PROVIDER': 'google',
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret',
            'SECRET_KEY': 'test_secret_key',
            'ADMIN_EMAILS': 'admin@example.com'
        })
        self.env_patch.start()
        
        # Initialize components
        login_manager = LoginManager()
        login_manager.init_app(self.app)
        
        self.user_manager = UserManager(self.temp_db.name)
        
        # User loader
        @login_manager.user_loader
        def load_user(user_id):
            return self.user_manager.get_user(user_id)
        
        self.app.register_blueprint(auth_bp)
        self.client = self.app.test_client()
    
    def teardown_method(self):
        """Cleanup test environment"""
        self.env_patch.stop()
        os.unlink(self.temp_db.name)
    
    def test_complete_auth_flow_simulation(self):
        """Test complete authentication flow simulation"""
        with self.app.app_context():
            # 1. Create user (simulating OAuth2 callback)
            user = self.user_manager.create_or_update_user(
                'test_123', 'test@example.com', 'Test User'
            )
            assert user is not None
            
            # 2. Test user permissions
            assert user.can_access_feature('chat') == True
            assert user.can_access_feature('admin_panel') == False
            
            # 3. Test admin user
            admin = self.user_manager.create_or_update_user(
                'admin_123', 'admin@example.com', 'Admin User'
            )
            assert admin.role == 'admin'
            assert admin.can_access_feature('admin_panel') == True
            
            # 4. Test rate limiting
            for _ in range(5):
                self.user_manager.increment_request_count('test_123')
            
            updated_user = self.user_manager.get_user('test_123')
            assert updated_user.request_count == 5

# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )

# Test fixtures
@pytest.fixture
def temp_database():
    """Create temporary database for testing"""
    temp_db = tempfile.NamedTemporaryFile(delete=False)
    temp_db.close()
    yield temp_db.name
    os.unlink(temp_db.name)

@pytest.fixture
def mock_oauth_env():
    """Mock OAuth2 environment variables"""
    with patch.dict(os.environ, {
        'OAUTH2_PROVIDER': 'google',
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret',
        'SECRET_KEY': 'test_secret_key'
    }):
        yield

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
