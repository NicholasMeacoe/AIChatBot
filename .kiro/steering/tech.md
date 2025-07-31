# Technology Stack

## Backend
- **Framework**: Flask 3.1.1 (Python web framework)
- **AI Integration**: Google Generative AI SDK (`google-generativeai`)
- **Database**: SQLite with `sqlite3` (built-in Python)
- **Environment**: Python-dotenv for configuration management

## Frontend
- **CSS Framework**: Tailwind CSS (CDN)
- **JavaScript**: Vanilla ES6+ with async/await patterns
- **UI Libraries**: 
  - Marked.js for Markdown rendering
  - Mermaid.js for diagram rendering
  - Highlight.js for syntax highlighting
- **Real-time**: Server-Sent Events (SSE) for streaming responses

## Key Dependencies
- **Image Processing**: Pillow, img2pdf, pytesseract (OCR)
- **PDF Handling**: PyPDF2
- **Web Scraping**: BeautifulSoup4, requests
- **Testing**: pytest with fixtures and mocking

## Architecture Pattern
- **Object-Oriented**: Main application class `GeminiChatApp`
- **Modular Features**: Separate modules in `features/` directory
- **Route Organization**: RESTful API endpoints with `/api/` prefix
- **Database Layer**: Direct SQLite integration with connection management

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
# or
python3 app.py

# Run tests
pytest
pytest -v  # verbose output
```

### Environment Setup
```bash
# Create .env file with required variables
echo "GOOGLE_API_KEY=your_key_here" > .env
echo "SECRET_KEY=your_secret_key" >> .env
```

### Database Management
```bash
# Database is auto-initialized on first run
# To reset database, delete the file:
rm chat_history.db
```

### Production Deployment
```bash
# Using Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## File Structure Conventions
- Main app logic in root-level Python files
- Feature modules in `features/` directory
- Templates in `templates/` directory (Jinja2)
- Static assets in `static/js/` directory
- Tests in `tests/` directory with pytest structure
- Context files restricted to `allowed_context/` directory