# Add OAuth2 Authentication and Authorization System

## 🎯 Overview

This PR implements a comprehensive OAuth2 authentication and authorization system for the Gemini Chat Flask App, addressing the security requirements outlined in the GitHub issue. The implementation provides secure user authentication, role-based access control, and rate limiting to protect the application and its resources.

## 🔐 Security Features Implemented

### Authentication (AuthN)
- **OAuth2 Integration**: Support for Google, GitHub, and custom OAuth2 providers
- **Secure Session Management**: Flask-Login integration with secure cookie handling
- **Multi-Provider Support**: Configurable OAuth2 provider selection
- **User Profile Management**: Complete user registration and profile system

### Authorization (AuthZ)
- **Role-Based Access Control**: User and Admin roles with different permissions
- **Feature-Level Permissions**: Granular control over app functionality
- **Rate Limiting**: Per-user request limits to prevent abuse
- **Admin Panel**: Complete user management interface for administrators

## 🚀 Key Features

### 1. Authentication System
- OAuth2 login with popular providers (Google, GitHub, custom)
- Secure session management with Flask-Login
- User registration and profile creation
- Login/logout functionality with proper redirects

### 2. Authorization & Permissions
- **User Role**: Chat access, view own history, context management, PDF conversion
- **Admin Role**: All user permissions + delete any history, user management, admin panel
- Feature-level permission checking with decorators
- Visual permission indicators in UI

### 3. Rate Limiting
- Configurable per-user request limits (default: 100 requests/hour)
- Visual rate limit indicators for users
- Admin controls for rate limit management
- Automatic request counting and reset

### 4. User Management
- Complete user database with SQLite backend
- Admin panel for user management
- Role assignment and modification
- User activation/deactivation controls

### 5. Enhanced Security
- CSRF protection via Flask's built-in features
- User data isolation (users only see their own chat history)
- Secure OAuth2 flow implementation
- Input validation and sanitization

## 📁 Files Added/Modified

### Core OAuth2 Implementation
- `auth_config.py` - OAuth2 configuration management
- `oauth_auth.py` - OAuth2 authentication logic and decorators
- `user_management.py` - User database operations and models
- `auth_routes.py` - Authentication routes and endpoints
- `app_with_oauth.py` - Main application with OAuth2 integration

### Templates & UI
- `templates/auth/login.html` - Modern login page with provider selection
- `templates/auth/profile.html` - User profile and permissions page
- `templates/auth/admin.html` - Admin panel for user management
- `templates/index_with_auth.html` - Updated main interface with auth features

### Configuration & Setup
- `.env.oauth.template` - Environment configuration template
- `requirements-oauth.txt` - OAuth2 dependencies
- `requirements-with-oauth.txt` - Complete requirements with OAuth2

### Documentation & Migration
- `README_OAUTH2.md` - Comprehensive setup and usage documentation
- `migrate_to_oauth.py` - Migration script for existing installations
- `PR_DESCRIPTION.md` - This pull request description

### Testing
- `test_oauth2.py` - Comprehensive test suite covering all OAuth2 functionality

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements-with-oauth.txt
```

### 2. Configure OAuth2 Provider

#### Google OAuth2 (Recommended)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth2 credentials
3. Add redirect URI: `http://localhost:5000/auth/callback`

#### GitHub OAuth2
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App
3. Set callback URL: `http://localhost:5000/auth/callback`

### 3. Environment Configuration
```bash
cp .env.oauth.template .env
# Edit .env with your OAuth2 credentials
```

### 4. Run the Application
```bash
python app_with_oauth.py
```

## 🔄 Migration from Non-OAuth Version

For existing installations, use the migration script:
```bash
python migrate_to_oauth.py
```

This script will:
- Backup existing data
- Update database schema
- Create OAuth2 configuration template
- Install required dependencies
- Provide step-by-step migration instructions

## 🧪 Testing

Run the comprehensive test suite:
```bash
pytest test_oauth2.py -v
```

Tests cover:
- OAuth2 configuration management
- User model and permissions
- Database operations
- Authentication flows
- Route protection
- Integration scenarios

## 📊 Database Changes

### New Tables
- `users` - User accounts and profiles
- `user_sessions` - Session management for rate limiting
- `user_chat_permissions` - Chat history access permissions

### Modified Tables
- `history` - Added `user_id` column for user association

## 🎨 UI/UX Improvements

### Login Experience
- Modern, responsive login page
- Provider-specific branding (Google, GitHub)
- Dark/light theme support
- Feature preview for new users

### Main Interface
- User avatar and info in header
- Rate limit indicators
- Permission status display
- Admin panel access for administrators

### Admin Panel
- User management dashboard
- Role assignment interface
- System statistics
- Rate limit controls

## 🔒 Security Considerations

### Production Deployment
- Use HTTPS in production
- Set secure `SECRET_KEY`
- Configure proper OAuth2 redirect URIs
- Enable rate limiting
- Regular security updates

### Data Protection
- User data isolation
- Secure session handling
- Input validation and sanitization
- SQL injection prevention

## 📈 Performance Impact

- Minimal performance overhead
- Efficient database queries with proper indexing
- Session-based authentication (no token validation on each request)
- Configurable rate limiting to prevent abuse

## 🔧 Configuration Options

All configuration is handled via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OAUTH2_PROVIDER` | OAuth2 provider (google/github/custom) | google |
| `ENABLE_ROLE_BASED_ACCESS` | Enable role-based access control | true |
| `DEFAULT_USER_ROLE` | Default role for new users | user |
| `ADMIN_EMAILS` | Comma-separated admin emails | - |
| `ENABLE_RATE_LIMITING` | Enable rate limiting | true |
| `RATE_LIMIT_PER_USER` | Requests per hour per user | 100 |

## 🐛 Backward Compatibility

- Original `app.py` remains unchanged and functional
- New OAuth2 version in `app_with_oauth.py`
- Existing chat history preserved during migration
- Context files and configurations maintained

## 📚 Documentation

Comprehensive documentation provided:
- `README_OAUTH2.md` - Complete setup and usage guide
- Inline code comments and docstrings
- Configuration examples and templates
- Troubleshooting guides

## 🎯 Resolves

This PR resolves the GitHub issue: **"Add authN and add authZ using OAuth2"**

### Requirements Met:
- ✅ **Authentication (AuthN)**: OAuth2 login with multiple providers
- ✅ **Authorization (AuthZ)**: Role-based access control with feature permissions
- ✅ **Security**: Secure session management, rate limiting, CSRF protection
- ✅ **User Management**: Admin panel for user and permission management
- ✅ **Documentation**: Comprehensive setup and usage documentation
- ✅ **Testing**: Complete test suite covering all functionality
- ✅ **Migration**: Smooth transition path for existing installations

## 🚀 Ready for Review

This implementation provides enterprise-grade authentication and authorization for the Gemini Chat application while maintaining ease of use and setup. The system is production-ready with comprehensive security features, extensive documentation, and thorough testing.

### Review Checklist:
- [ ] OAuth2 configuration and setup
- [ ] User management and permissions
- [ ] Security implementation review
- [ ] Database schema changes
- [ ] UI/UX improvements
- [ ] Documentation completeness
- [ ] Test coverage
- [ ] Migration process

The implementation follows security best practices and provides a solid foundation for future enhancements while maintaining the simplicity and functionality that makes the Gemini Chat app valuable to users.
