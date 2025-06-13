# Gemini Chat Flask App

This is a web-based chat application powered by Google's Gemini AI models, built using the Flask framework. It allows users to interact with various Gemini models, provides a filterable and deletable history of the conversation, and includes features to add file, folder, or URL context to the chat prompts, manage active context, summarize context, and convert JPEG images to PDF (optionally with OCR).

## Features

*   **Multi-Model Gemini Integration:** Connects to the Google Generative AI API. Fetches available Gemini models and allows users to select the desired model via a dropdown. Uses a fallback default (`gemini-2.5-pro-exp-03-25`) if API fetching fails or the key is missing.
*   **Web Interface:** A clean, responsive HTML interface (`templates/index.html`) built with Bootstrap 5 (supporting dark mode) for sending messages and viewing chat history.
*   **Streaming Responses:** Bot responses are streamed back to the client in real-time using Server-Sent Events (SSE).
*   **Chat History Management:**
    *   Conversations are stored locally in an SQLite database (`chat_history.db`).
    *   History can be viewed filtered by date using a dropdown.
    *   History for a specific date can be deleted.
*   **Context Injection & Management:**
    *   **File/Folder Context:** Reference local files or folders within a designated `allowed_context` directory using the `@ {path}` syntax or the context menu. Content (for files) or listings (for folders) are prepended to the prompt.
    *   **URL Context:** Reference web URLs using the `@ {url}` syntax or the context menu. The app fetches the URL, extracts text content (HTML/Text), and prepends it to the prompt.
    *   **Active Context:** Added context items (files, folders, URLs) appear in an "Active Context" list. Only items in this list are sent with the *next* message. This list can be managed (items removed individually or all cleared).
    *   **Context Summarization:** A button allows summarizing the content of all items currently in the "Active Context" list using the selected Gemini model.
    *   **Security:** Prevents access outside the `allowed_context` directory (using `realpath` and path validation). Enforces file size limits (`MAX_FILE_SIZE_MB`) and URL content limits (`MAX_URL_CONTENT_BYTES`).
*   **Image to PDF Conversion:**
    *   Upload multiple JPEG/JPG images.
    *   Convert the selected images into a single downloadable PDF file.
    *   Optional OCR (Optical Character Recognition) using Tesseract to make the text in the PDF selectable (requires Tesseract installation).
*   **Mermaid Diagram Rendering:** Bot responses containing Mermaid diagram code blocks (```mermaid ... ```) are automatically rendered as diagrams in the chat interface.
*   **Error Handling:** Handles API key issues, file/URL access problems, model loading errors, network errors, and context processing errors, displaying relevant messages to the user.

## Requirements

*   Python 3.x
*   Flask
*   Google Generative AI SDK (`google-generativeai`)
*   python-dotenv (for loading API keys from `.env` file)
*   Requests (for fetching models and URL context)
*   Beautiful Soup 4 (`beautifulsoup4`) (for parsing URL HTML content)
*   Pillow (for image validation)
*   img2pdf (for basic image-to-PDF conversion)
*   PyPDF2 (for merging OCR-processed PDFs)
*   html (for HTML encoding chat history)
*   **Optional (for OCR):** Tesseract OCR Engine. Must be installed separately and accessible in the system's PATH. See [Tesseract Installation Guide](https://tesseract-ocr.github.io/tessdoc/Installation.html).
*   **Optional (for OCR):** pytesseract Python wrapper (`pip install pytesseract`)

You can install the required Python dependencies using `pip`:
```bash
pip install Flask google-generativeai python-dotenv requests beautifulsoup4 Pillow img2pdf PyPDF2 pytesseract html
```
*(Note: Update `requirements.txt` if you use one)*

## Setup

1.  **Clone the repository (or ensure you have the files):**
    Make sure you have `app.py`, `templates/index.html`.
2.  **Create the `allowed_context` directory:**
    This directory must exist in the same location as `app.py`. The application will attempt to create it if it doesn't exist. Place any files or folders you want to reference in your chat prompts inside this directory.
    ```bash
    mkdir allowed_context
    ```
3.  **Create a `.env` file:**
    In the same directory as `app.py`, create a file named `.env` and add your Google API key:
    ```
    GOOGLE_API_KEY=YOUR_API_KEY_HERE
    ```
    Replace `YOUR_API_KEY_HERE` with your actual API key obtained from Google AI Studio or Google Cloud. The app will attempt to fetch available models using this key.
4.  **Install Dependencies:**
    ```bash
    pip install Flask google-generativeai python-dotenv requests beautifulsoup4 Pillow img2pdf PyPDF2 pytesseract
    ```
5.  **Install Tesseract (Optional):**
    If you want to use the OCR feature for PDF conversion, install Tesseract OCR following the instructions for your operating system: [Tesseract Installation Guide](https://tesseract-ocr.github.io/tessdoc/Installation.html). Ensure the `tesseract` command is available in your system's PATH.
6.  **Initialize Database:**
    The application automatically creates the `chat_history.db` SQLite database file on the first run if it doesn't exist.

## Usage

1.  **Run the Flask Application:**
    ```bash
    python app.py
    ```
    The server will start, typically on `http://0.0.0.0:5000/`. The console will show the API key status, fetched models, database location, and server address.
2.  **Open in Browser:**
    Navigate to `http://localhost:5000` or `http://<your-machine-ip>:5000` in your web browser.
3.  **Select Model:**
    Choose the desired Gemini model from the "Model" dropdown.
4.  **Manage History:**
    *   Use the "History" dropdown to view conversations from a specific date or "All History".
    *   If a specific date is selected, the "Delete" button becomes active, allowing you to remove all entries for that date.
5.  **Add Context:**
    *   Type `@` in the message input to open the context menu.
    *   Select "Files" or "Folders" to browse and choose items from the `allowed_context` directory.
    *   Select "Url", enter a URL (starting with `http://` or `https://`), and click "Add".
    *   Alternatively, type the context directly:
        *   File: `Summarize this: @ report.txt`
        *   Folder: `List contents: @ project_files/`
        *   URL: `What is this page about? @ https://example.com`
        *   Paths/URLs can be quoted: `Analyze: @ "src/main.py"` or `@ "https://example.com/article"`
    *   Added context items appear in the "Active Context" area above the input box.
    *   Manage active context: Remove individual items using the 'x' button next to them, or clear all items with the "Clear All" button.
    *   **Important:** Only the items listed in the "Active Context" area when you send a message will be prepended to that message's prompt.
6.  **Summarize Context:**
    Click the "Summarize" button (icon looks like lines of text) next to the Send button to ask the selected model to summarize the content of all items currently in the "Active Context" list.
7.  **Chat:**
    Type your message in the input box and press Enter or click the "Send" button (paper airplane icon). The message, along with any active context, will be sent to the selected Gemini model.
8.  **Convert Images to PDF:**
    *   Use the "Convert JPEGs to PDF" section at the bottom.
    *   Click "Choose Files" to select one or more `.jpeg` or `.jpg` files.
    *   Optionally, check the "Make text selectable (OCR)?" box (requires Tesseract).
    *   Click "Convert & Download". The generated PDF will be downloaded.
9.  **View Diagrams:** If the bot's response includes Mermaid code (e.g., for flowcharts, sequence diagrams), it will be rendered visually in the chat.

## Database

*   The chat history is stored in `chat_history.db`.
*   The `history` table contains:
    *   `id`: Unique identifier for the interaction.
    *   `timestamp`: Time the interaction was saved.
    *   `user_message`: The original message sent by the user (without prepended context).
    *   `bot_response`: The full response received from the Gemini model.
    *   `context_info`: A JSON string containing details about the processed context paths/URLs (files, folders, URLs) that were active for that specific message.

## Running the App

```bash
python app.py
```

The application will print status messages to the console. Access the application through your web browser at the displayed address (e.g., `http://0.0.0.0:5000/`).

## Running Tests

To run the automated tests, first install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Then, run pytest from the root directory of the project:

```bash
pytest
```
