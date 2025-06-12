import pytest
from unittest.mock import patch, MagicMock, call
import os
import json # For generate_response_stream tests

# Functions to test
from gemini_utils import (
    configure_client, # Renamed from configure_gemini_api
    get_available_models,
    generate_response_stream,
    generate_summary,
    FETCHED_MODELS_CACHE, # To inspect/clear cache
    DEFAULT_MODEL_NAME as GEMINI_UTILS_DEFAULT_MODEL_NAME # Use this for clarity
)
# Other imports
from config import GOOGLE_API_KEY as CONFIG_API_KEY # Original key from app's config
import gemini_utils # To mock client at module level or genai directly
import requests # For requests.exceptions.RequestException

# --- Tests for configure_client ---

def test_configure_client_success(monkeypatch): # Renamed test
    """Test successful Gemini client configuration."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "test_api_key")
    with patch('gemini_utils.genai.Client') as mock_genai_client_constructor:
        mock_genai_client_instance = MagicMock()
        mock_genai_client_constructor.return_value = mock_genai_client_instance

        assert configure_client() == True # Renamed call
        mock_genai_client_constructor.assert_called_once_with(api_key="test_api_key")
        assert gemini_utils.client == mock_genai_client_instance

def test_configure_client_no_key(monkeypatch, capsys): # Renamed test
    """Test client configuration when GOOGLE_API_KEY is not set."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', None)
    monkeypatch.setattr(gemini_utils, 'client', None)
    assert configure_client() == False # Renamed call
    captured = capsys.readouterr()
    assert "GOOGLE_API_KEY not found" in captured.out
    assert gemini_utils.client is None

def test_configure_client_exception(monkeypatch, capsys): # Renamed test
    """Test client configuration when genai.Client() raises an exception."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "test_api_key")
    monkeypatch.setattr(gemini_utils, 'client', None)
    with patch('gemini_utils.genai.Client', side_effect=Exception("Config error")) as mock_genai_client_constructor:
        assert configure_client() == False # Renamed call
        captured = capsys.readouterr()
        assert "Error configuring Gemini client: Config error" in captured.out # Updated expected message
        assert gemini_utils.client is None


# --- Tests for get_available_models ---

@pytest.fixture(autouse=True)
def clear_model_cache_and_restore_key(monkeypatch):
    """Clears the model cache and restores API key before each test."""
    FETCHED_MODELS_CACHE.clear()
    # Restore the API key in gemini_utils to its original value from config
    # This helps isolate tests that modify it.
    # Set a consistent dummy API key for all tests in this module,
    # rather than relying on CONFIG_API_KEY which might be None.
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "dummy_api_key_for_tests")
    # It's also good practice to reset the client if tests modify it directly,
    # though mock_gemini_client fixture should handle its state.
    # monkeypatch.setattr(gemini_utils, 'client', None) # Or setup via configure_gemini_api if needed by test

def test_get_available_models_no_api_key(monkeypatch, capsys):
    # This test specifically tests behavior when API key is None.
    # The autouse fixture runs first, sets it to "dummy_api_key_for_tests".
    # So, we need to override it here for this specific test case.
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', None)
    # Ensure client is None because configure_client would fail
    monkeypatch.setattr(gemini_utils, 'client', None)

    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME]
    captured = capsys.readouterr()
    assert "API key is missing" in captured.out

def test_get_available_models_sdk_success(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    # Ensure the global client in gemini_utils is the mocked one for this test
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)

    # Configure the mock client's return value for list_models
    # The mock_gemini_client fixture in conftest.py already sets up some defaults.
    # We can override here if needed or use its defaults.
    # Using default from conftest: models/DEFAULT_MODEL_NAME, models/gemini-1.0-pro

    # Expected: ['gemini-1.0-pro', DEFAULT_MODEL_NAME] (sorted)
    # The conftest mock_gemini_client defines:
    # mock_model_default.name = f"models/{DEFAULT_MODEL_NAME}"
    # mock_model_pro.name = "models/gemini-1.0-pro"
    # list.return_value = [mock_model_default, mock_model_pro]

    expected_models = sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, 'gemini-1.0-pro'])

    models = get_available_models()
    assert sorted(models) == expected_models # Compare sorted as order might vary if default is added
    assert sorted(gemini_utils.FETCHED_MODELS_CACHE) == expected_models # Access via module
    mock_gemini_client.models.list.assert_called_once()

def test_get_available_models_sdk_no_suitable_models(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.list.return_value = [
        MagicMock(name="models/unsupported-model", supported_actions=['embedContent'])
    ]
    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME]
    captured = capsys.readouterr()
    assert "No suitable models found via SDK" in captured.out

# Using the mock_requests_get fixture from conftest.py
def test_get_available_models_sdk_fails_http_api_success(mock_requests_get, mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.list.side_effect = Exception("SDK Error")

    # Configure mock_requests_get (which is requests.get's mock)
    mock_requests_get.return_value.json.return_value = {
        "models": [
            {"name": "models/gemini-1.5-flash-latest", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-1.0-pro", "supportedGenerationMethods": ["generateContent"]},
        ]
    }
    mock_requests_get.return_value.raise_for_status = MagicMock() # Ensure it doesn't raise

    # gemini_utils.py sorts the models from API if found
    expected_api_models = sorted(['gemini-1.5-flash-latest', 'gemini-1.0-pro'])
    # Then it ensures DEFAULT_MODEL_NAME is present
    final_expected_models = sorted(list(set(expected_api_models + [GEMINI_UTILS_DEFAULT_MODEL_NAME])))


    models = get_available_models()
    assert sorted(models) == final_expected_models
    mock_requests_get.assert_called_once()

def test_get_available_models_sdk_fails_http_api_fails(mock_requests_get, mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.list.side_effect = Exception("SDK Error")
    mock_requests_get.side_effect = requests.exceptions.RequestException("HTTP Error")

    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME]
    captured = capsys.readouterr()
    assert "Error fetching models from direct API: HTTP Error" in captured.out

def test_get_available_models_caching(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    # Default mock from conftest: [DEFAULT_MODEL_NAME, 'gemini-1.0-pro']
    expected_initial_models = sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, 'gemini-1.0-pro'])

    # First call - should call API
    models1 = get_available_models()
    assert sorted(models1) == expected_initial_models
    mock_gemini_client.models.list.assert_called_once()

    # Second call - should use cache. We check this by asserting the mock wasn't called again.
    # And by checking the print message via capsys.
    models2 = get_available_models()
    assert sorted(models2) == expected_initial_models
    mock_gemini_client.models.list.assert_called_once() # Still called only once in total

    captured = capsys.readouterr() # Capture output from the second call
    assert "Using cached model list." in captured.out


def test_get_available_models_force_refresh(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)

    get_available_models() # First call
    assert mock_gemini_client.models.list.call_count == 1

    get_available_models(force_refresh=True) # Second call with force_refresh
    assert mock_gemini_client.models.list.call_count == 2

def test_get_available_models_default_model_added(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)

    other_model_name = "gemini-other-model"
    mock_model_other = MagicMock(supported_actions=['generateContent'])
    mock_model_other.name = f"models/{other_model_name}" # Explicitly set the 'name' attribute
    # Ensure DEFAULT_MODEL_NAME is not part of the mock SDK response initially
    assert other_model_name != GEMINI_UTILS_DEFAULT_MODEL_NAME
    mock_gemini_client.models.list.return_value = [mock_model_other]

    models = get_available_models()
    assert GEMINI_UTILS_DEFAULT_MODEL_NAME in models
    assert other_model_name in models
    assert sorted(models) == sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, other_model_name])


# --- Tests for generate_response_stream ---

def test_generate_response_stream_success(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    # mock_gemini_client from conftest:
    # iter([MagicMock(text="Test response chunk 1."), MagicMock(text="Test response chunk 2.")])

    prompt = "Test prompt"
    model_name = GEMINI_UTILS_DEFAULT_MODEL_NAME

    stream_data = list(generate_response_stream(prompt, model_name))

    mock_gemini_client.models.generate_content_stream.assert_called_once_with(model=model_name, contents=prompt)

    assert len(stream_data) == 3 # 2 chunks + 1 end_stream
    assert json.loads(stream_data[0].split("data: ")[1]) == {"text": "Test response chunk 1."}
    assert json.loads(stream_data[1].split("data: ")[1]) == {"text": "Test response chunk 2."}
    assert json.loads(stream_data[2].split("data: ")[1]) == {"end_stream": True}

def test_generate_response_stream_api_error(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.generate_content_stream.side_effect = Exception("API Error")

    stream_data = list(generate_response_stream("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME))

    assert len(stream_data) == 1
    error_response = json.loads(stream_data[0].split("data: ")[1])
    assert "error" in error_response
    assert "API Error" in error_response["error"]

def test_generate_response_stream_no_text_in_chunk(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_chunk_with_text = MagicMock(text="Hello")
    mock_chunk_no_text = MagicMock(text=None)
    mock_gemini_client.models.generate_content_stream.return_value = iter([mock_chunk_with_text, mock_chunk_no_text])

    stream_data = list(generate_response_stream("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME))

    assert len(stream_data) == 2
    assert json.loads(stream_data[0].split("data: ")[1]) == {"text": "Hello"}
    assert json.loads(stream_data[1].split("data: ")[1]) == {"end_stream": True}


# --- Tests for generate_summary ---

def test_generate_summary_success(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    # mock_gemini_client from conftest: MagicMock(text="Test summary response.")

    prompt = "Summarize this"
    model_name = GEMINI_UTILS_DEFAULT_MODEL_NAME

    summary = generate_summary(prompt, model_name)

    mock_gemini_client.models.generate_content.assert_called_once_with(model_name, prompt)
    assert summary == "Test summary response."

def test_generate_summary_api_error(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.generate_content.side_effect = Exception("Summary API Error")

    with pytest.raises(Exception, match="Summary API Error"):
        generate_summary("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME)

def test_generate_summary_value_error(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.generate_content.side_effect = ValueError("Model config error")

    with pytest.raises(ValueError, match="Model config error"):
        generate_summary("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME)

# Example of testing a print statement within a more complex function like get_available_models
# This is already covered by checking capsys in test_get_available_models_no_api_key etc.
# but here's an explicit example if needed for other tests.
def test_get_available_models_prints_sdk_error(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.list.side_effect = Exception("Custom SDK Error")
    # Fallback also fails
    with patch('gemini_utils.requests.get', side_effect=requests.exceptions.RequestException("HTTP Error")):
        get_available_models()

    captured = capsys.readouterr()
    assert "Error fetching models via SDK: Custom SDK Error" in captured.out
    assert "Error fetching models from direct API: HTTP Error" in captured.out
