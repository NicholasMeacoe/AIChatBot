# Project Structure

## Root Level Files
- **`app.py`** - Main application entry point with `GeminiChatApp` class
- **`config.py`** - Configuration management and environment variables
- **`database.py`** - Database initialization and utilities
- **`requirements.txt`** - Python dependencies
- **`.env`** - Environment variables (API keys, secrets)
- **`chat_history.db`** - SQLite database (auto-generated)

## Directory Organization

### `/features/`
Modular feature implementations:
- **`multimodal.py`** - Image/audio/video processing
- **`search.py`** - Search and indexing functionality
- **`templates.py`** - Template management system
- **`analytics.py`** - Usage analytics
- **`collaboration.py`** - Multi-user features
- **`voice.py`** - Voice interaction capabilities
- **`__init__.py`** - Package initialization

### `/templates/`
Jinja2 HTML templates:
- **`index.html`** - Main chat interface
- **`clean_index.html`** - Simplified interface variant
- Multiple backup/test templates for development

### `/static/js/`
Frontend JavaScript modules:
- **`conversation-manager.js`** - Chat conversation handling
- **`enhanced-features.js`** - Advanced UI features
- **`markdown-fix.js`** - Markdown rendering fixes
- **`rendering-fix.js`** - Message display improvements
- Multiple fix/diagnostic scripts for specific issues

### `/tests/`
Pytest test suite:
- **`conftest.py`** - Test configuration and fixtures
- **`test_database.py`** - Database testing
- **`/routes/`** - Route-specific tests
- **`/utils/`** - Utility function tests

### `/allowed_context/`
Secure file context directory:
- User-uploaded files for chat context
- Sandboxed file access for security
- Auto-created on first run

### `/plugins/`
Plugin system:
- **`example_plugin.py`** - Plugin template
- Extensible architecture for custom features

### `/templates_data/`
Template storage:
- **`templates.json`** - Saved chat templates

## Code Organization Patterns

### Main Application (`app.py`)
- Single `GeminiChatApp` class containing all core logic
- Route definitions within the class
- Database operations integrated
- Streaming response handlers

### Feature Modules
- Each feature in separate file under `features/`
- Class-based organization (e.g., `MultiModalProcessor`, `SearchManager`)
- Import into main app as needed

### Database Schema
```sql
conversations (id, name, timestamp, system_prompt, model)
history (id, conversation_id, timestamp, user_message, bot_response, context_info)
```

### API Endpoints
- **`/api/conversations`** - Conversation management
- **`/api/chat`** - Main chat streaming endpoint
- **`/api/context/*`** - Context file/folder operations
- **`/api/chat_multimodal`** - Multimodal chat endpoint

## Security Boundaries
- File access restricted to `allowed_context/` directory
- Path traversal protection with `secure_filename()`
- Input sanitization for all user data
- Environment variable isolation