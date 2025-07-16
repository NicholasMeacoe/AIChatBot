# Troubleshooting Guide

## Quick Fixes Applied

### ✅ **Fixed Issues:**
1. **Send Button & Enter Key** - Now properly connected to sendMessage()
2. **New Chat Button** - Now creates conversations via API
3. **History Loading** - Fixed API endpoint calls
4. **Error Handling** - Added comprehensive error catching
5. **Debugging** - Added console logging for troubleshooting

### 🔧 **How to Debug:**

1. **Open Browser Console** (F12 → Console tab)
2. **Start the app**: `python3 app.py`
3. **Visit**: http://localhost:5000
4. **Check console for logs**:
   - `🚀 Initializing ModernGeminiChat...`
   - `📋 Loading conversations...`
   - `💬 Sending message...`

### 🐛 **Common Issues:**

**"Error loading conversations"**
- Check if app.py is running
- Verify database exists (chat_history.db)
- Check browser console for specific error

**"Cannot send message"**
- Ensure a conversation is selected
- Check console for "Conversation ID: null"
- Try creating a new chat first

**"New Chat doesn't work"**
- Check browser console for API errors
- Verify /api/conversations POST endpoint

### 🧪 **Test API Directly:**
```bash
# Test if server is running
curl http://localhost:5000/api/conversations

# Test creating new conversation
curl -X POST http://localhost:5000/api/conversations
```

### 📊 **Expected Console Output:**
```
🚀 Initializing ModernGeminiChat...
✅ ModernGeminiChat initialized
📋 Loading conversations...
📋 Conversations response: 200
📋 Found conversations: 1
📋 Loading first conversation: Default Conversation
```

### 🔄 **If Still Not Working:**
1. **Clear browser cache** (Ctrl+F5)
2. **Check browser console** for JavaScript errors
3. **Restart the application**
4. **Verify .env file** has GOOGLE_API_KEY

The application should now work properly with:
- ✅ Send button functionality
- ✅ Enter key to send messages
- ✅ New chat creation
- ✅ Conversation history loading
- ✅ Real-time message streaming
