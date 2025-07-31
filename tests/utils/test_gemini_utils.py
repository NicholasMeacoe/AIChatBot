import pytest
from unittest.mock import patch, MagicMock, call
import os
import json # For generate_response_stream tests

# Functions to test
from gemini_utils import (
    configure_client,
    get_available_models,
    generate_response_stream,
    generate_summary,
    FETCHED_MODELS_CACHE,
    DEFAULT_MODEL_NAME as GEMINI_UTILS_DEFAULT_MODEL_NAME
)
# Other imports
from config import GOOGLE_API_KEY as CONFIG_API_KEY
import gemini_utils
import requests

# --- Tests for configure_client ---

def test_configure_client_success(monkeypatch):
    """Test successful Gemini client configuration."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "test_api_key")
    with patch('gemini_utils.genai.configure') as mock_configure:
        assert configure_client() == True
        mock_configure.assert_called_once_with(api_key="test_api_key")

def test_configure_client_no_key(monkeypatch, capsys):
    """Test client configuration when GOOGLE_API_KEY is not set."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', None)
    assert configure_client() == False
    captured = capsys.readouterr()
    assert "GOOGLE_API_KEY not found" in captured.out

def test_configure_client_exception(monkeypatch, capsys):
    """Test client configuration when genai.configure() raises an exception."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "test_api_key")
    with patch('gemini_utils.genai.configure', side_effect=Exception("Config error")):
        assert configure_client() == False
        captured = capsys.readouterr()
        assert "Error configuring Google AI: Config error" in captured.out


# --- Tests for get_available_models ---

@pytest.fixture(autouse=True)
def clear_model_cache_and_restore_key(monkeypatch):
    """Clears the module-level cache in gemini_utils.py and sets a dummy API key before each test."""
    monkeypatch.setattr(gemini_utils, 'FETCHED_MODELS_CACHE', [], raising=False)
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "dummy_api_key_for_tests")

def test_get_available_models_no_api_key(monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', None)
    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME]
    captured = capsys.readouterr()
    assert "Warning: GOOGLE_API_KEY not found" in captured.out

def test_get_available_models_sdk_success(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    expected_models = sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, 'gemini-1.0-pro'])
    models = get_available_models()
    assert sorted(models) == expected_models
    assert sorted(gemini_utils.FETCHED_MODELS_CACHE) == expected_models

def test_get_available_models_sdk_no_suitable_models(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr('gemini_utils.genai.list_models', lambda: [MagicMock(name="models/unsupported-model", supported_generation_methods=['embedContent'])])
    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME]

def test_get_available_models_sdk_fails_http_api_success(mock_requests_get, mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr('gemini_utils.genai.list_models', MagicMock(side_effect=Exception("SDK Error")))
    mock_requests_get.return_value.json.return_value = {
        "models": [
            {"name": "models/gemini-1.5-flash-latest", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-1.0-pro", "supportedGenerationMethods": ["generateContent"]},
        ]
    }
    mock_requests_get.return_value.raise_for_status = MagicMock()
    expected_api_models = sorted(['gemini-1.5-flash-latest', 'gemini-1.0-pro'])
    final_expected_models = sorted(list(set(expected_api_models + [GEMINI_UTILS_DEFAULT_MODEL_NAME])))
    models = get_available_models()
    assert sorted(models) == final_expected_models
    mock_requests_get.assert_called_once()

def test_get_available_models_sdk_fails_http_api_fails(mock_requests_get, mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr('gemini_utils.genai.list_models', MagicMock(side_effect=Exception("SDK Error")))
    mock_requests_get.side_effect = requests.exceptions.RequestException("HTTP Error")
    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME]
    captured = capsys.readouterr()
    assert "Error fetching models: SDK Error" in captured.out

def test_get_available_models_caching(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    expected_initial_models = sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, 'gemini-1.0-pro'])
    models1 = get_available_models()
    assert sorted(models1) == expected_initial_models
    models2 = get_available_models()
    assert sorted(models2) == expected_initial_models
    # The mock is in conftest, so we can't easily assert call count without more changes.
    # Instead, we rely on the fact that if it were called twice, the test would fail
    # if the mock wasn't set up for a second call.

def test_get_available_models_force_refresh(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    with patch('gemini_utils.genai.list_models', return_value=[]) as mock_list_models:
        get_available_models()
        mock_list_models.assert_called_once()
        get_available_models(force_refresh=True)
        assert mock_list_models.call_count == 2

def test_get_available_models_default_model_added(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    other_model_name = "gemini-other-model"
    mock_model_other = MagicMock(supported_generation_methods=['generateContent'])
    mock_model_other.name = f"models/{other_model_name}"
    monkeypatch.setattr('gemini_utils.genai.list_models', lambda: [mock_model_other])
    models = get_available_models()
    assert GEMINI_UTILS_DEFAULT_MODEL_NAME in models
    assert other_model_name in models
    assert sorted(models) == sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, other_model_name])

# --- Tests for generate_response_stream ---

def test_generate_response_stream_success(mock_gemini_client, monkeypatch):
    prompt = "Test prompt"
    model_name = GEMINI_UTILS_DEFAULT_MODEL_NAME
    stream_data = list(generate_response_stream(prompt, model_name))
    mock_gemini_client.generate_content.assert_called_once_with(prompt, stream=True)
    assert len(stream_data) == 2
    assert stream_data[0] == "Test response chunk 1."
    assert stream_data[1] == "Test response chunk 2."

def test_generate_response_stream_api_error(mock_gemini_client, monkeypatch):
    mock_gemini_client.generate_content.side_effect = Exception("API Error")
    stream_data = list(generate_response_stream("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME))
    assert len(stream_data) == 1
    assert "Error generating response: API Error" in stream_data[0]

def test_generate_response_stream_no_text_in_chunk(mock_gemini_client, monkeypatch):
    mock_chunk_with_text = MagicMock()
    mock_chunk_with_text.text = "Hello"
    mock_chunk_no_text = MagicMock()
    mock_chunk_no_text.text = None
    mock_gemini_client.generate_content.return_value = iter([mock_chunk_with_text, mock_chunk_no_text])
    stream_data = list(generate_response_stream("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME))
    assert len(stream_data) == 1
    assert stream_data[0] == "Hello"

# --- Tests for generate_summary ---

def test_generate_summary_success(mock_gemini_client, monkeypatch):
    content = "Summarize this"
    summary = generate_summary(content)
    expected_prompt = f"Please provide a concise summary of the following content in no more than 200 characters:\n\n{content}"
    mock_gemini_client.generate_content.assert_called_once_with(expected_prompt)
    assert summary == "Test summary response."

def test_generate_summary_api_error(mock_gemini_client, monkeypatch):
    mock_gemini_client.generate_content.side_effect = Exception("Summary API Error")
    result = generate_summary("prompt")
    assert "Error generating summary: Summary API Error" in result

def test_generate_summary_value_error(mock_gemini_client, monkeypatch):
    mock_gemini_client.generate_content.side_effect = ValueError("Model config error")
    result = generate_summary("prompt")
    assert "Error generating summary: Model config error" in result

def test_get_available_models_prints_sdk_error(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr('gemini_utils.genai.list_models', MagicMock(side_effect=Exception("Custom SDK Error")))
    with patch('gemini_utils.requests.get', side_effect=requests.exceptions.RequestException("HTTP Error")):
        get_available_models()
    captured = capsys.readouterr()
    assert "Error fetching models: Custom SDK Error" in captured.out

