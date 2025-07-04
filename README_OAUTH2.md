# OAuth2 Authentication Implementation

This document describes the OAuth2 authentication and authorization system added to the Gemini Chat Flask App.

## Overview

The OAuth2 implementation provides:
- **Authentication**: Users must log in via OAuth2 providers (Google, GitHub, or custom)
- **Authorization**: Role-based access control for different features
- **Rate Limiting**: Per-user request limits to prevent abuse
- **User Management**: Admin panel for managing users and permissions
- **Session Management**: Secure session handling with Flask-Login

## Features Added

### 1. Authentication System
- OAuth2 integration with multiple providers
- Secure session management
- User profile management
- Login/logout functionality

### 2. Authorization & Permissions
- Role-based access control (user, admin)
- Feature-level permissions
- Admin-only functions (user management, history deletion)

### 3. Rate Limiting
- Per-user request counting
- Configurable limits
- Visual indicators for users

### 4. User Management
- User registration and profile creation
- Admin panel for user management
- Role assignment and modification

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-oauth.txt
```

### 2. Configure OAuth2 Provider

#### Option A: Google OAuth2
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set application type to "Web application"
6. Add authorized redirect URI: `http://localhost:5000/auth/callback`
7. Copy Client ID and Client Secret

#### Option B: GitHub OAuth2
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in application details:
   - Application name: "Gemini Chat"
   - Homepage URL: `http://localhost:5000`
   - Authorization callback URL: `http://localhost:5000/auth/callback`
4. Copy Client ID and Client Secret

#### Option C: Custom OAuth2 Provider
Configure your OAuth2 provider with:
- Redirect URI: `http://localhost:5000/auth/callback`
- Required scopes: `openid`, `email`, `profile`

### 3. Environment Configuration

Copy the template and configure:
```bash
cp .env.oauth.template .env
```

Edit `.env` with your OAuth2 credentials:
```env
# Required
GOOGLE_API_KEY=your_google_api_key_here
SECRET_KEY=your_super_secret_key_here

# OAuth2 Provider (choose one)
OAUTH2_PROVIDER=google
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Admin Configuration
ADMIN_EMAILS=admin@example.com,another-admin@example.com
```

### 4. Database Setup

The application will automatically create the required database tables:
- `users` - User accounts and profiles
- `user_sessions` - Session management
- `user_chat_permissions` - Chat history permissions
- `history` - Updated with user associations

## Usage

### 1. Starting the Application

```bash
python app_with_oauth.py
```

### 2. First Login
1. Navigate to `http://localhost:5000`
2. You'll be redirected to the login page
3. Click "Continue with [Provider]"
4. Complete OAuth2 authentication
5. You'll be redirected back to the chat interface

### 3. Admin Setup
1. Add your email to `ADMIN_EMAILS` in `.env`
2. Log in - you'll automatically get admin role
3. Access admin panel via user dropdown menu

## File Structure

```
├── auth_config.py          # OAuth2 configuration management
├── oauth_auth.py           # OAuth2 authentication logic
├── user_management.py      # User database operations
├── auth_routes.py          # Authentication routes
├── app_with_oauth.py       # Main application with OAuth2
├── templates/auth/         # Authentication templates
│   ├── login.html         # Login page
│   ├── profile.html       # User profile
│   └── admin.html         # Admin panel
├── .env.oauth.template     # Environment configuration template
└── requirements-oauth.txt  # OAuth2 dependencies
```

## Security Features

### 1. Authentication Security
- Secure OAuth2 flow implementation
- Session management with Flask-Login
- CSRF protection via Flask's built-in features
- Secure cookie handling

### 2. Authorization Security
- Role-based access control
- Feature-level permissions
- Admin-only functions protection
- User data isolation

### 3. Rate Limiting
- Per-user request tracking
- Configurable limits
- Automatic reset mechanisms
- Visual feedback to users

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OAUTH2_PROVIDER` | OAuth2 provider (google/github/custom) | google | Yes |
| `GOOGLE_CLIENT_ID` | Google OAuth2 Client ID | - | If using Google |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 Client Secret | - | If using Google |
| `GITHUB_CLIENT_ID` | GitHub OAuth2 Client ID | - | If using GitHub |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth2 Client Secret | - | If using GitHub |
| `SECRET_KEY` | Flask secret key | - | Yes |
| `ENABLE_ROLE_BASED_ACCESS` | Enable role-based access control | true | No |
| `DEFAULT_USER_ROLE` | Default role for new users | user | No |
| `ADMIN_EMAILS` | Comma-separated admin emails | - | No |
| `ENABLE_RATE_LIMITING` | Enable rate limiting | true | No |
| `RATE_LIMIT_PER_USER` | Requests per hour per user | 100 | No |

### User Roles

| Role | Permissions |
|------|-------------|
| `user` | Chat access, view own history, context management, PDF conversion |
| `admin` | All user permissions + delete any history, user management, admin panel |

### Feature Permissions

| Feature | User | Admin |
|---------|------|-------|
| Chat Access | ✅ | ✅ |
| View History | ✅ | ✅ |
| Delete Own History | ✅ | ✅ |
| Delete Any History | ❌ | ✅ |
| Context Management | ✅ | ✅ |
| PDF Conversion | ✅ | ✅ |
| Admin Panel | ❌ | ✅ |
| User Management | ❌ | ✅ |

## API Endpoints

### Authentication Endpoints
- `GET /auth/login` - Login page
- `GET /auth/authorize` - OAuth2 authorization redirect
- `GET /auth/callback` - OAuth2 callback handler
- `GET /auth/logout` - Logout user
- `GET /auth/profile` - User profile page
- `GET /auth/admin` - Admin panel (admin only)
- `GET /auth/status` - Authentication status (API)

### Protected Endpoints
All existing chat endpoints now require authentication:
- `GET /` - Main chat interface
- `POST /chat` - Send chat message
- `GET /history` - Get chat history
- `POST /history/delete` - Delete chat history

## Troubleshooting

### Common Issues

1. **OAuth2 Configuration Error**
   - Check `.env` file has correct credentials
   - Verify redirect URI matches OAuth2 app configuration
   - Ensure OAuth2 provider is correctly set

2. **Database Issues**
   - Delete existing database files to recreate tables
   - Check file permissions for database directory

3. **Rate Limiting Issues**
   - Check `RATE_LIMIT_PER_USER` setting
   - Admin can reset rate limits via admin panel

4. **Permission Denied**
   - Check user role assignment
   - Verify admin emails configuration
   - Check feature permissions in user management

### Debug Mode

Enable debug logging by setting Flask debug mode:
```python
app.run(debug=True)
```

## Migration from Non-OAuth Version

1. **Backup existing data**:
   ```bash
   cp chat_history.db chat_history.db.backup
   ```

2. **Install OAuth2 dependencies**:
   ```bash
   pip install -r requirements-oauth.txt
   ```

3. **Configure OAuth2** following setup instructions

4. **Update database schema** (automatic on first run)

5. **Test authentication** with a test user

6. **Configure admin users** via environment variables

## Production Deployment

### Security Considerations
1. Use HTTPS in production
2. Set secure `SECRET_KEY`
3. Configure proper OAuth2 redirect URIs
4. Enable rate limiting
5. Regular security updates

### Environment Variables for Production
```env
SECRET_KEY=very_secure_random_string_here
OAUTH2_PROVIDER=google
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_USER=50
```

### Database Backup
Regular backups of user database:
```bash
sqlite3 users.db ".backup users_backup_$(date +%Y%m%d).db"
```

## Support

For issues related to OAuth2 implementation:
1. Check this documentation
2. Review error logs
3. Verify OAuth2 provider configuration
4. Test with minimal configuration

## License

This OAuth2 implementation maintains the same license as the original Gemini Chat application.
