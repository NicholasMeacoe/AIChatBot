# Modern Gemini Chat Application

A modern, dark-themed web chat interface for Google's Gemini AI models with comprehensive functionality and a professional UI.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
Create a `.env` file:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secret_key_here
```

### 3. Run the Application
```bash
python3 app.py
```

### 4. Access the Interface
Open your browser to: **http://localhost:5000**

## ✨ Features

### 🎨 **Modern Dark UI**
- Professional dark theme using Tailwind CSS
- Responsive design that works on all devices
- Smooth animations and transitions
- Clean, modern interface components

### 💬 **Chat Functionality**
- **35+ Gemini Models** - Access to all available Gemini AI models
- **Real-time Streaming** - Messages appear as they're generated
- **Complete Message Display** - No truncation issues
- **Conversation Management** - Multiple persistent chat threads
- **System Prompts** - Customize AI behavior per conversation

### 📁 **Context Integration**
- **File Context** - Reference local files in your prompts
- **Folder Context** - Include directory listings
- **URL Context** - Fetch and include web content
- **Context Management** - Easy add/remove context items
- **Security** - Sandboxed file access within `allowed_context` directory

### 📊 **Advanced Features**
- **History Management** - Persistent conversation history with SQLite
- **Date Filtering** - Filter conversations by specific dates
- **PDF Conversion** - Convert images to PDF with optional OCR
- **Syntax Highlighting** - Code blocks with proper formatting
- **Mermaid Diagrams** - Automatic diagram rendering
- **Markdown Support** - Rich text formatting in messages

## 🏗️ **Architecture**

### **Backend (Flask)**
- Object-oriented design with clean separation of concerns
- Streaming chat responses with Server-Sent Events
- Comprehensive error handling and logging
- Secure context processing with path validation
- SQLite database with proper schema and relationships

### **Frontend (Modern JavaScript)**
- ES6+ features with async/await patterns
- Real-time message streaming
- Responsive modal dialogs
- Context management interface
- Auto-resizing input areas

### **Database Schema**
```sql
conversations
├── id (PRIMARY KEY)
├── name
├── timestamp
├── system_prompt
└── model

history
├── id (PRIMARY KEY)
├── conversation_id (FOREIGN KEY)
├── timestamp
├── user_message
├── bot_response
└── context_info
```

## 🔒 **Security Features**

- **Path Traversal Protection** - Prevents access outside allowed directories
- **Input Sanitization** - HTML encoding and validation
- **File Size Limits** - Configurable limits for uploads and context
- **URL Validation** - Secure URL fetching with timeouts
- **CORS Headers** - Proper cross-origin resource sharing

## 📱 **Usage Guide**

### **Starting a Conversation**
1. The application loads with a default conversation
2. Click "New Chat" to create additional conversations
3. Select your preferred Gemini model from the dropdown
4. Optionally set a system prompt to customize AI behavior
5. Start chatting!

### **Adding Context**
1. Click "Context" to open the context management panel
2. Use "Add File", "Add Folder", or "Add URL" buttons
3. Select items from the modal dialogs
4. Context items appear in your active context list
5. They're automatically included in your next message

### **Managing History**
- All conversations are automatically saved to SQLite database
- Switch between conversations using the sidebar
- Each conversation maintains its own history and settings
- Use the history filter to view messages from specific dates

## 🔧 **Configuration**

### **Environment Variables**
```env
GOOGLE_API_KEY=your_api_key          # Required: Gemini API key
SECRET_KEY=your_secret_key           # Optional: Flask secret key
```

### **Application Settings**
The application includes sensible defaults:
- **Max File Size**: 10MB for context files
- **Max URL Content**: 2MB for web content
- **Request Timeout**: 10 seconds for URL fetching
- **Database**: SQLite with automatic initialization

## 🐛 **Troubleshooting**

### **Common Issues**

**"No models available"**
- Check your `GOOGLE_API_KEY` in the `.env` file
- Verify the API key has proper permissions

**"Context directory not found"**
- The `allowed_context` directory is created automatically
- Ensure write permissions in the application directory

**"Database errors"**
- Delete `chat_history.db` to reset the database
- Check file permissions in the application directory

**"Messages not displaying completely"**
- This has been fixed in the new version
- Ensure you're using the updated `app.py`

## 🚀 **Production Deployment**

For production use:

1. **Use a WSGI Server**:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. **Set Environment Variables**:
```bash
export FLASK_ENV=production
export GOOGLE_API_KEY=your_key
```

3. **Configure Reverse Proxy** (nginx example):
```nginx
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 📝 **What's New**

This version includes major improvements over the original:

- ✅ **Complete message display** - No more truncated responses
- ✅ **Modern dark theme** - Professional UI with Tailwind CSS
- ✅ **Clean architecture** - Object-oriented, maintainable code
- ✅ **Proper error handling** - Comprehensive error management
- ✅ **Real-time streaming** - Smooth message delivery
- ✅ **Enhanced security** - Better input validation and sanitization
- ✅ **Responsive design** - Works perfectly on all devices

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**🎉 Enjoy your modern Gemini Chat experience!**

Start the application with `python3 app.py` and visit http://localhost:5000
