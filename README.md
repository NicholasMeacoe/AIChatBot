# Gemini Chat Flask App

This is a simple web-based chat application powered by Google's Gemini AI model, built using the Flask framework. It allows users to interact with the Gemini model, provides a history of the conversation, and includes a feature to add file or folder context to the chat prompts.

## Features

*   **Gemini Integration:** Connects to the Google Generative AI API to provide chat responses using the specified Gemini model (default: `gemini-2.5-pro-exp-03-25`).
*   **Web Interface:** A clean HTML interface (`templates/index.html`) for sending messages and viewing the chat history.
*   **Streaming Responses:** Bot responses are streamed back to the client in real-time using Server-Sent Events (SSE).
*   **Chat History:** Conversations are stored locally in an SQLite database (`chat_history.db`).
*   **Context Injection:** Users can reference local files or folders within a designated `allowed_context` directory using the `@ {path}` syntax in their messages. The content of the file or the listing of the folder contents will be prepended to the prompt sent to the Gemini model.
    *   Security measures are in place to prevent access outside the `allowed_context` directory.
    *   File size limits (`MAX_FILE_SIZE_MB`) are enforced.
*   **Error Handling:** Basic error handling for API key issues, file access problems, and network errors.

## Requirements

*   Python 3.x
*   Flask
*   Google Generative AI SDK (`google-generativeai`)
*   python-dotenv (for loading API keys from `.env` file)

You can install the Python dependencies using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Setup

1.  **Clone the repository (or ensure you have the files):**
    Make sure you have `app.py`, `templates/index.html`, and `requirements.txt`.
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
    Replace `YOUR_API_KEY_HERE` with your actual API key obtained from Google AI Studio or Google Cloud.
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Initialize Database:**
    The application automatically creates the `chat_history.db` SQLite database file on the first run if it doesn't exist.

## Usage

1.  **Run the Flask Application:**
    ```bash
    python app.py
    ```
    The server will start, typically on `http://0.0.0.0:5000/`.
2.  **Open in Browser:**
    Navigate to `http://localhost:5000` or `http://<your-machine-ip>:5000` in your web browser.
3.  **Chat:**
    Type your messages in the input box and press Enter or click "Send".
4.  **Use Context:**
    To add context from a file or folder within the `allowed_context` directory, use the `@` symbol followed by the relative path within that directory.
    *   Example (file): `Summarize this document: @ report.txt`
    *   Example (folder): `What files are in this project? @ project_files/`
    *   Paths can be quoted: `Analyze this code: @ "src/main.py"`
    *   Context warnings or errors (e.g., file not found, too large) will appear above the bot's response.

## Database

*   The chat history is stored in `chat_history.db`.
*   The `history` table contains:
    *   `id`: Unique identifier for the interaction.
    *   `timestamp`: Time the interaction was saved.
    *   `user_message`: The original message sent by the user (including `@ {path}` directives).
    *   `bot_response`: The full response received from the Gemini model.
    *   `context_info`: A JSON string containing details about the processed context paths for that message (if any).

## Running the App

```bash
python app.py
```

The application will print status messages to the console, including the database file location and the address where the server is running. Access the application through your web browser.
