import pytest
from app_factory import create_app as create_flask_app
import os
import tempfile
from unittest.mock import patch, MagicMock

# Import database functions and config values
from database import init_db as initialize_database
from config import ALLOWED_CONTEXT_DIR as ORIGINAL_ALLOWED_CONTEXT_DIR_CONFIG # Renamed to avoid clash
from config import ALLOWED_CONTEXT_DIR_NAME as ORIGINAL_ALLOWED_CONTEXT_DIR_NAME_CONFIG # Renamed
from config import DEFAULT_MODEL_NAME


@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session with an isolated DB."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    flask_app = create_flask_app()
    flask_app.config.update({
        "TESTING": True,
        "DB_NAME": db_path,
        "WTF_CSRF_ENABLED": False,
    })

    import config # Import here to ensure monkeypatching affects the loaded module
    original_db_name_module_level = config.DB_NAME
    config.DB_NAME = db_path

    with flask_app.app_context():
        initialize_database()

    yield flask_app

    # Teardown
    config.DB_NAME = original_db_name_module_level
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

@pytest.fixture(scope='session')
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


@pytest.fixture(scope='session')
def mock_gemini_client():
    """Mocks the Gemini API client used in gemini_utils.py for the entire session."""
    # Assuming gemini_utils.client is the instance of genai.Client
    with patch('gemini_utils.client', autospec=True) as mock_client:
        # Mock for get_available_models (client.models.list())
        mock_model_default = MagicMock()
        # The name attribute on the SDK's Model object is the full path like 'models/gemini-1.5-pro-latest'
        mock_model_default.name = f"models/{DEFAULT_MODEL_NAME}"
        mock_model_default.supported_actions = ['generateContent'] # Corrected based on gemini_utils SDK usage

        mock_model_pro = MagicMock()
        mock_model_pro.name = "models/gemini-1.0-pro"
        mock_model_pro.supported_actions = ['generateContent']

        # client.models.list() returns an iterable of Model objects
        mock_client.models.list.return_value = [mock_model_default, mock_model_pro]

        # Mock for generate_response_stream (client.models.generate_content_stream())
        mock_chunk = MagicMock()
        mock_chunk.text = "Test response chunk."
        # generate_content_stream returns an iterable (stream) of GenerateContentResponse objects
        mock_client.models.generate_content_stream.return_value = iter([MagicMock(text="Test response chunk 1."), MagicMock(text="Test response chunk 2.")])

        # Mock for generate_summary (client.models.generate_content())
        mock_summary_response = MagicMock() # This is a GenerateContentResponse object
        mock_summary_response.text = "Test summary response."
        mock_client.models.generate_content.return_value = mock_summary_response

        # Mock for model instantiation/validation if client.models.get() is used
        # client.models.get() returns a Model object
        mock_client.models.get.return_value = MagicMock(name=f"models/{DEFAULT_MODEL_NAME}", supported_actions=['generateContent'])

        yield mock_client

@pytest.fixture(scope='function')
def mock_requests_get():
    """Mocks requests.get for function scope."""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock(spec=requests.Response) # Use spec for better mocking
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

# TODO: Still need to consider mocking for file system operations more granularly
# for context_processing unit tests (pyfakefs or individual os module patches).
# The temp_allowed_context_dir is good for routes.
