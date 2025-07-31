import pytest
from app_factory import create_app as create_flask_app
import os
import tempfile
from unittest.mock import patch, MagicMock
import requests # Added for mock_requests_get
import PyPDF2 # Added for MockPdfMerger

# Import database functions and config values
from database import init_db as initialize_database
from config import ALLOWED_CONTEXT_DIR as ORIGINAL_ALLOWED_CONTEXT_DIR_CONFIG # Renamed to avoid clash
from config import ALLOWED_CONTEXT_DIR_NAME as ORIGINAL_ALLOWED_CONTEXT_DIR_NAME_CONFIG # Renamed
from config import DEFAULT_MODEL_NAME
import config as config_module_for_patching # For pytest_configure
import gemini_utils as gemini_utils_module_for_patching # For pytest_configure

# Store original values to restore them later
ORIGINAL_ENV_GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
ORIGINAL_CONFIG_GOOGLE_API_KEY = config_module_for_patching.GOOGLE_API_KEY
ORIGINAL_GEMINI_UTILS_GOOGLE_API_KEY = gemini_utils_module_for_patching.GOOGLE_API_KEY


def pytest_configure(config): # Changed argument name config_pytest to config
    """Sets up global configuration for tests, like setting a dummy API key."""
    os.environ["GOOGLE_API_KEY"] = "test_api_key_from_pytest_configure"
    # Force update the config module variable as it's set at import time from os.getenv
    config_module_for_patching.GOOGLE_API_KEY = "test_api_key_from_pytest_configure"
    # Also update gemini_utils module variable as it imports from config
    gemini_utils_module_for_patching.GOOGLE_API_KEY = "test_api_key_from_pytest_configure"

def pytest_unconfigure(config): # Changed argument name config_pytest to config
    """Restores original configuration after tests."""
    if ORIGINAL_ENV_GOOGLE_API_KEY is None:
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
    else:
        os.environ["GOOGLE_API_KEY"] = ORIGINAL_ENV_GOOGLE_API_KEY

    config_module_for_patching.GOOGLE_API_KEY = ORIGINAL_CONFIG_GOOGLE_API_KEY
    gemini_utils_module_for_patching.GOOGLE_API_KEY = ORIGINAL_GEMINI_UTILS_GOOGLE_API_KEY


@pytest.fixture(scope='function') # Changed scope from 'session' to 'function'
def app(monkeypatch): # Added monkeypatch for config.DB_NAME
    """Create and configure a new app instance for each test function with an isolated DB."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    # Ensure config.GOOGLE_API_KEY is the test key when app is created
    # This is now handled by pytest_configure, but double-check or rely on it.
    # For safety, we can re-apply monkeypatch to the specific config instance if needed,
    # but pytest_configure should make it available process-wide before app_factory imports config.

    flask_app = create_flask_app() # app_factory will import config and gemini_utils
    flask_app.config.update({
        "TESTING": True,
        "DB_NAME": db_path, # Flask app's config for DB_NAME
        "WTF_CSRF_ENABLED": False,
    })

    # Monkeypatch the DB_NAME in the config module directly for database.py functions
    # as they access config.DB_NAME dynamically.
    monkeypatch.setattr(config_module_for_patching, 'DB_NAME', db_path, raising=False)

    with flask_app.app_context():
        initialize_database()
        # The patch for 'gemini_utils.configure_client' during app context can be removed
        # as app_factory.py no longer calls it in test mode, and mock_gemini_client fixture
        # handles its own calls to configure_client.

    yield flask_app

    # DB_NAME restoration is handled by monkeypatch's teardown.
    os.close(db_fd)
    try:
        os.remove(db_path)
        # print(f"Test database {db_path} removed.") # Keep test output clean
    except OSError:
        # print(f"Error removing test database {db_path}: {e}") # Keep test output clean
        pass


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function') # Changed from session to function
def temp_allowed_context_dir():
    """Creates a temporary 'allowed_context' directory for testing file operations."""
    with tempfile.TemporaryDirectory(prefix="test_allowed_context_") as tmpdir_path:
        import config # Import here to ensure monkeypatching affects the loaded module
        original_allowed_context_dir_module_level = config.ALLOWED_CONTEXT_DIR
        original_allowed_context_dir_name_module_level = config.ALLOWED_CONTEXT_DIR_NAME

        config.ALLOWED_CONTEXT_DIR = tmpdir_path
        config.ALLOWED_CONTEXT_DIR_NAME = os.path.basename(tmpdir_path)

        # TemporaryDirectory creates the directory. Make sure it's writable if needed by tests.
        # print(f"Using temporary allowed_context_dir: {tmpdir_path}") # Keep test output clean

        yield tmpdir_path

        # Restore original values in config module
        config.ALLOWED_CONTEXT_DIR = original_allowed_context_dir_module_level
        config.ALLOWED_CONTEXT_DIR_NAME = original_allowed_context_dir_name_module_level
        # print(f"Restored ALLOWED_CONTEXT_DIR to: {original_allowed_context_dir_module_level}") # Keep test output clean


@pytest.fixture(scope='function') # Changed to function scope
def mock_gemini_client(monkeypatch):
    """Mocks the Gemini API client used in gemini_utils.py for each test function."""
    # Clear gemini_utils cache and client before each test using this fixture
    monkeypatch.setattr('gemini_utils.FETCHED_MODELS_CACHE', [], raising=False) # Corrected cache name

    # GOOGLE_API_KEY is set by the 'app' fixture.
    # We patch genai.GenerativeModel so that when gemini_utils functions call it,
    # it receives our mock instance.
    with patch('gemini_utils.genai.GenerativeModel') as MockedGenerativeModel:
        mock_model_instance = MagicMock() # This is the mock for the genai.GenerativeModel *instance*
        MockedGenerativeModel.return_value = mock_model_instance

        # 1. Mock list_models for get_available_models()
        mock_sdk_model_default = MagicMock()
        mock_sdk_model_default.name = f"models/{DEFAULT_MODEL_NAME}"
        mock_sdk_model_default.supported_generation_methods=['generateContent']

        mock_sdk_model_pro = MagicMock()
        mock_sdk_model_pro.name = "models/gemini-1.0-pro"
        mock_sdk_model_pro.supported_generation_methods=['generateContent']

        # This is a change from the original code. list_models is a function on the genai module, not the model instance.
        monkeypatch.setattr('gemini_utils.genai.list_models', lambda: [mock_sdk_model_default, mock_sdk_model_pro])


        # 2. Mock generate_content for generate_response_stream() and generate_response()
        mock_stream_chunk_1 = MagicMock()
        mock_stream_chunk_1.text = "Test response chunk 1."
        mock_stream_chunk_2 = MagicMock()
        mock_stream_chunk_2.text = "Test response chunk 2."
        
        mock_summary_response = MagicMock()
        mock_summary_response.text = "Test summary response."

        # Have generate_content return a stream for streaming calls, and a single response for non-streaming.
        def side_effect(*args, **kwargs):
            if kwargs.get('stream'):
                return iter([mock_stream_chunk_1, mock_stream_chunk_2])
            return mock_summary_response

        mock_model_instance.generate_content.side_effect = side_effect
        
        import gemini_utils
        gemini_utils.configure_client()

        yield mock_model_instance

@pytest.fixture(scope='function')
def mock_requests_get():
    """Mocks requests.get for function scope."""
    with patch('requests.get') as mock_get:
        # Now that 'requests' is imported, this spec should work.
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'text/html; charset=utf-8'}
        mock_response.json.return_value = {}
        mock_response.text = "Mocked HTML content <p>Hello</p>"
        mock_response.content = b"Mocked HTML content <p>Hello</p>" # For URL processing
        # For iter_content (used in fetch_and_process_url)
        mock_response.iter_content.return_value = iter([b"chunk1 ", b"chunk2"])
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        yield mock_get

@pytest.fixture(scope='function')
def mock_pytesseract():
    """Mocks pytesseract.image_to_pdf_or_hocr for function scope."""
    # This function is directly imported and used in pdf_utils.py
    with patch('pdf_utils.pytesseract.image_to_pdf_or_hocr') as mock_ocr:
        mock_ocr.return_value = b"searchable_pdf_bytes_from_ocr"
        yield mock_ocr

@pytest.fixture(scope='function')
def mock_img2pdf_convert():
    """Mocks img2pdf.convert for function scope."""
    # This function is directly imported and used in pdf_utils.py
    with patch('pdf_utils.img2pdf.convert') as mock_convert:
        mock_convert.return_value = b"pdf_bytes_from_img2pdf"
        yield mock_convert

@pytest.fixture(scope='function')
def MockPdfMerger(): # Renamed to follow pytest fixture naming conventions (lowercase start)
    """Mocks PyPDF2.PdfMerger for function scope."""
    # Path to where PdfMerger is imported in the module under test (pdf_utils.py)
    with patch('pdf_utils.PdfMerger') as mock_merger_class:
        # mock_merger_class is the mock for the PdfMerger class itself.
        # We need to mock the instance that will be created from it.
        mock_merger_instance = MagicMock(spec=PyPDF2.PdfMerger)
        mock_merger_class.return_value = mock_merger_instance
        yield mock_merger_instance # Yield the instance, as that's what the code will interact with

# TODO: Still need to consider mocking for file system operations more granularly
# for context_processing unit tests (pyfakefs or individual os module patches).
# The temp_allowed_context_dir is good for routes.
