# Modern Gemini Chat - Complete Rewrite

A completely rewritten, modern web-based chat application powered by Google's Gemini AI models with a sleek dark theme and enhanced functionality.

## 🎨 **New Features & Improvements**

### **Modern Dark UI**
- **Tailwind CSS** - Modern, responsive design system
- **Dark Theme** - Easy on the eyes with professional appearance
- **Responsive Layout** - Works perfectly on desktop and mobile
- **Smooth Animations** - Polished user experience with transitions
- **Modern Icons** - Clean SVG icons throughout the interface

### **Enhanced Architecture**
- **Clean Code Structure** - Object-oriented design with proper separation of concerns
- **Streaming Responses** - Real-time message streaming with proper error handling
- **Robust Error Handling** - Comprehensive error management and user feedback
- **Secure Context Processing** - Enhanced security for file and URL processing
- **Modern JavaScript** - ES6+ features with proper async/await patterns

### **Fixed Functionality**
- ✅ **Complete Message Display** - All message content now displays properly
- ✅ **Proper History Management** - Conversation-based history with date filtering
- ✅ **Context Integration** - Seamless file, folder, and URL context processing
- ✅ **Model Selection** - Dynamic model loading with 35+ available models
- ✅ **Real-time Streaming** - Smooth message streaming without truncation
- ✅ **Database Integrity** - Proper SQLite schema with foreign key constraints

## 🚀 **Quick Start**

### **1. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Set Up Environment**
Create a `.env` file:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secret_key_here
```

### **3. Run the Application**
```bash
python3 app_new.py
```

### **4. Access the Interface**
Open your browser to: **http://localhost:5000**

## 📋 **Features Overview**

### **💬 Chat Management**
- **Multiple Conversations** - Create and manage separate chat threads
- **Persistent History** - All conversations saved to SQLite database
- **Model Selection** - Choose from 35+ available Gemini models
- **System Prompts** - Customize AI behavior per conversation
- **Real-time Streaming** - Messages appear as they're generated

### **📁 Context Integration**
- **File Context** - Reference local files in your prompts
- **Folder Context** - Include directory listings
- **URL Context** - Fetch and include web content
- **Context Management** - Add, remove, and manage active context items
- **Security** - Sandboxed file access within `allowed_context` directory

### **🎨 User Interface**
- **Dark Theme** - Professional dark color scheme
- **Responsive Design** - Works on all screen sizes
- **Syntax Highlighting** - Code blocks with proper highlighting
- **Markdown Support** - Rich text formatting in messages
- **Mermaid Diagrams** - Automatic diagram rendering
- **Copy Functionality** - Easy copying of code and content

### **🔧 Advanced Features**
- **PDF Conversion** - Convert images to PDF with optional OCR
- **History Filtering** - Filter conversations by date
- **Context Panel** - Collapsible context management
- **Auto-resize Input** - Smart textarea that grows with content
- **Typing Indicators** - Visual feedback during generation

## 🏗️ **Architecture**

### **Backend (Flask)**
```
app_new.py
├── GeminiChatApp (Main Application Class)
├── Database Management (SQLite)
├── Context Processing (Files, URLs)
├── Streaming Chat Handler
├── PDF Conversion
└── API Endpoints
```

### **Frontend (Modern JavaScript)**
```
templates/chat.html
├── ModernGeminiChat (Main UI Class)
├── Message Management
├── Context Management
├── Modal Handlers
├── Real-time Streaming
└── Responsive Design
```

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

## 🧪 **Testing**

Run the comprehensive test suite:
```bash
python3 test_new_app.py
```

Tests include:
- ✅ Import validation
- ✅ Database operations
- ✅ Application initialization
- ✅ Context directory setup
- ✅ API endpoint functionality

## 📱 **Usage Guide**

### **Starting a Conversation**
1. Click "New Chat" to create a conversation
2. Select your preferred Gemini model
3. Optionally set a system prompt
4. Start chatting!

### **Adding Context**
1. Click "Context" to open the context panel
2. Use "Add File", "Add Folder", or "Add URL" buttons
3. Select items from the modal dialogs
4. Context items appear in your active context list
5. They're automatically included in your next message

### **Managing History**
- All conversations are automatically saved
- Use the history filter dropdown to view specific dates
- Switch between conversations using the sidebar
- Each conversation maintains its own history and settings

### **Customizing Behavior**
- **Model Selection**: Choose from 35+ available models
- **System Prompts**: Set custom instructions for the AI
- **Context Items**: Include relevant files, folders, or web content

## 🔧 **Configuration**

### **Environment Variables**
```env
GOOGLE_API_KEY=your_api_key          # Required: Gemini API key
SECRET_KEY=your_secret_key           # Optional: Flask secret key
```

### **Application Settings**
```python
MAX_FILE_SIZE_MB = 10               # Maximum file size for context
MAX_URL_CONTENT_BYTES = 2MB         # Maximum URL content size
REQUEST_TIMEOUT = 10                # URL request timeout in seconds
```

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

**"Streaming not working"**
- Ensure your browser supports Server-Sent Events
- Check browser console for JavaScript errors

### **Performance Tips**
- Keep context files under 10MB for optimal performance
- Use specific system prompts to improve response quality
- Clear unused context items to reduce processing time

## 📊 **Comparison with Original**

| Feature | Original App | New Modern App |
|---------|-------------|----------------|
| **UI Framework** | Bootstrap 5 | Tailwind CSS |
| **Theme** | Light/Dark Toggle | Modern Dark |
| **Architecture** | Monolithic | Object-Oriented |
| **Message Display** | ❌ Truncated | ✅ Complete |
| **Error Handling** | Basic | Comprehensive |
| **Code Quality** | Mixed | Clean & Modern |
| **Responsiveness** | Limited | Fully Responsive |
| **Performance** | Moderate | Optimized |
| **Maintainability** | Difficult | Easy |

## 🚀 **Production Deployment**

For production use:

1. **Use a WSGI Server**:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app_new:app.app
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

## 📝 **License**

This project is open source and available under the MIT License.

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

---

**🎉 Enjoy your modern Gemini Chat experience!**

The application now provides a professional, reliable, and feature-rich interface for interacting with Google's Gemini AI models.
