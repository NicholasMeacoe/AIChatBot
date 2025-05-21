import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Model Configuration ---
DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # Updated default based on common availability
# Note: Free tier limits can change. Users should verify current limits.
# Keys should match the API model name (e.g., "models/gemini-1.5-flash-latest")
# We will fetch the actual model names from the API, this is just for limits.
FREE_TIER_LIMITS = {
    "models/gemini-1.5-flash-latest": {"RPM": 60, "RPD": 1500, "TPM": 1_000_000},
    "models/gemini-1.0-pro": {"RPM": 60, "RPD": None, "TPM": None},
    "models/gemini-1.5-pro-latest": {"RPM": 2, "RPD": 50, "TPM": 1_000_000},
    # Add other known models and their potential limits if needed
}

# --- File Handling ---
MAX_FILE_SIZE_MB = 10
MAX_FILE_READ_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_CONTEXT_DIR_NAME = "allowed_context"
ALLOWED_CONTEXT_DIR = os.path.abspath(ALLOWED_CONTEXT_DIR_NAME)
ALLOWED_PDF_EXTENSIONS = {'jpeg', 'jpg'} # For image to PDF conversion

# --- URL Processing ---
MAX_URL_CONTENT_BYTES = 2 * 1024 * 1024 # Limit URL content size (e.g., 2MB)
REQUEST_TIMEOUT = 10 # Seconds for URL requests

# --- Database ---
DB_NAME = 'chat_history.db'

# --- Application Settings ---
DEBUG_MODE = True # Set to False in production
HOST = '0.0.0.0'
PORT = 5000

# --- Directory Setup ---
def ensure_allowed_context_dir():
    """Creates the allowed context directory if it doesn't exist."""
    if not os.path.exists(ALLOWED_CONTEXT_DIR):
        try:
            os.makedirs(ALLOWED_CONTEXT_DIR)
            print(f"Created allowed context directory: {ALLOWED_CONTEXT_DIR}")
            return True
        except OSError as e:
            print(f"Error creating allowed context directory '{ALLOWED_CONTEXT_DIR}': {e}")
            return False
    return True

# --- Tesseract ---
# Optional: Specify Tesseract path if not in system PATH
# TESSERACT_CMD = '/usr/local/bin/tesseract' # Example for macOS/Linux
# TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Example for Windows
# if 'TESSERACT_CMD' in locals():
#     import pytesseract
#     pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
