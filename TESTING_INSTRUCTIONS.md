# Testing the Enhanced Upload Functionality

## 🚀 Quick Start

### 1. Start the Server
```bash
cd /mnt/c/Source/AIChatBot
python app.py
```

You should see output like:
```
🚀 Starting Modern Gemini Chat Server...
📊 Database: /mnt/c/Source/AIChatBot/chat_history.db
📁 Context Directory: /mnt/c/Source/AIChatBot/allowed_context
🤖 Available Models: 35
🌐 Server: http://0.0.0.0:5000
```

### 2. Test the Upload Feature

#### Option A: Using the Main Interface
1. Open your browser and go to `http://localhost:5000`
2. Look for the context panel on the right side
3. Click the **"Upload Files"** button (blue button)
4. You should see a modal with a drag-and-drop area
5. Either:
   - Drag files directly onto the drop zone
   - Click "Browse Files" to select files
6. Preview your files and click "Upload"
7. Files should appear in the context panel with file type icons

#### Option B: Using the Test Page
1. Open `http://localhost:5000/test_upload.html` in your browser
2. This is a simple test interface for the upload functionality
3. Drag files or click "Select Files"
4. Click "Upload Files" to test

### 3. Verify Upload Works

#### Check the Backend
- Look at the server console for upload logs
- Check the `allowed_context` folder for uploaded files
- Files should have unique names like `filename_20250711_120000_abc12345.ext`

#### Check the Frontend
- Open browser developer tools (F12)
- Look at the Console tab for debug messages
- You should see messages like:
  ```
  🔄 Starting upload of 1 files
  📎 Adding file 1: test.txt text/plain 25
  🚀 Sending upload request to /api/context/upload
  📡 Upload response status: 200
  ✅ Upload successful: {uploaded_files: [...]}
  ```

## 🐛 Troubleshooting

### "Upload failed: NOT FOUND" Error

This error means the upload endpoint isn't being found. Check:

1. **Server is running**: Make sure you see the server startup messages
2. **Correct URL**: The endpoint should be `/api/context/upload`
3. **No proxy issues**: Try accessing `http://localhost:5000/api/context/upload` directly

### Files Not Appearing in Context

1. **Check browser console** for JavaScript errors
2. **Verify file types** are supported (see list below)
3. **Check server logs** for upload processing errors

### Server Won't Start

1. **Check Python version**: Use Python 3.7+
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Check environment**: Make sure `.env` file exists with `GOOGLE_API_KEY`

## 📋 Supported File Types

### Images (with multimodal AI support)
- JPEG (.jpg, .jpeg) 🖼️
- PNG (.png) 🖼️
- GIF (.gif) 🖼️
- BMP (.bmp) 🖼️
- WebP (.webp) 🖼️

### Documents
- PDF (.pdf) 📕
- Word (.doc, .docx) 📘
- Text (.txt, .md) 📄
- JSON (.json) 📋
- CSV (.csv) 📊

### Media (for future features)
- Audio (.mp3, .wav, .m4a, .ogg) 🎵
- Video (.mp4, .avi, .mov, .mkv) 🎬

## 🧪 Manual API Testing

You can test the API directly using curl:

### Test Upload Endpoint
```bash
curl -X POST -F "files=@test.txt" http://localhost:5000/api/context/upload
```

Expected response:
```json
{
  "uploaded_files": ["test_20250711_120000_abc12345.txt"],
  "success_count": 1
}
```

### Test Check Images Endpoint
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"context_items": ["image.jpg", "document.txt"]}' \
  http://localhost:5000/api/context/check_images
```

Expected response:
```json
{
  "has_images": true,
  "image_count": 1,
  "image_files": ["image.jpg"]
}
```

## 🎯 Testing Multimodal Features

### With Images
1. Upload an image file (JPG, PNG, etc.)
2. Select a vision-capable model (Gemini 1.5 Pro or Flash)
3. Ask a question about the image: "What do you see in this image?"
4. The system should automatically use multimodal processing

### Debug Multimodal
Check the browser console for:
```
🖼️ Images detected: true, Vision model: true, Using multimodal: true
```

## 📊 Expected Behavior

### Successful Upload Flow
1. **File Selection**: Files appear in preview with icons
2. **Upload Progress**: Progress bar shows during upload
3. **Context Addition**: Files appear in context panel with type icons
4. **Visual Feedback**: Success message and modal closes

### Error Handling
- **Invalid file types**: Clear error message
- **Upload failures**: Specific error details
- **Network issues**: Connection error message

## 🔧 Advanced Testing

### Test Large Files
- Try uploading files of different sizes
- Check for proper error handling on oversized files

### Test Multiple Files
- Select multiple files at once
- Verify all are processed correctly

### Test Drag and Drop
- Drag files from file explorer
- Verify hover effects work
- Test dropping multiple files

### Test Image Processing
- Upload various image formats
- Check for proper thumbnail generation
- Verify metadata extraction

## 📝 Logging and Debugging

### Server-side Logs
Look for these messages in the server console:
- File upload attempts
- Processing results
- Error messages

### Client-side Debugging
Enable verbose logging by opening browser console and running:
```javascript
// Enable debug mode
localStorage.setItem('debug', 'true');
```

## ✅ Success Criteria

The upload functionality is working correctly if:

1. ✅ Files can be uploaded via drag-and-drop
2. ✅ Files can be uploaded via file browser
3. ✅ Files appear in context panel with correct icons
4. ✅ Image files are detected for multimodal processing
5. ✅ Upload progress is shown during transfer
6. ✅ Error messages are clear and helpful
7. ✅ Files are securely stored in allowed_context directory
8. ✅ Multimodal chat works with uploaded images

If all these work, your enhanced upload functionality is ready! 🎉
