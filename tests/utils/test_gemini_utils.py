import pytest
from unittest.mock import patch, MagicMock, call
import os
import json # For generate_response_stream tests

import pytest
from unittest.mock import patch, MagicMock, call
import os
import json # For generate_response_stream tests

# Functions to test
from gemini_utils import (
    configure_client,
    get_available_models,
    generate_response_stream,
    generate_summary
)
import gemini_utils # For monkeypatching module-level variables like GOOGLE_API_KEY, client
from config import DEFAULT_MODEL_NAME as CONFIG_DEFAULT_MODEL_NAME # This is already prefixed
import requests # For requests.exceptions.RequestException

# GEMINI_UTILS_DEFAULT_MODEL_NAME should be the one from config, which is already prefixed
GEMINI_UTILS_DEFAULT_MODEL_NAME = CONFIG_DEFAULT_MODEL_NAME

# --- Tests for configure_client ---

def test_configure_client_success(monkeypatch):
    """Test successful Gemini client configuration."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "test_api_key")
    with patch('gemini_utils.genai.Client') as mock_genai_client_constructor:
        mock_genai_client_instance = MagicMock()
        mock_genai_client_constructor.return_value = mock_genai_client_instance

        assert configure_client() == True
        # genai.Client() is called without api_key if GOOGLE_API_KEY is set in env
        mock_genai_client_constructor.assert_called_once_with()
        assert gemini_utils.client == mock_genai_client_instance

def test_configure_client_no_key(monkeypatch, capsys):
    """Test client configuration when GOOGLE_API_KEY is not set."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', None)
    monkeypatch.setattr(gemini_utils, 'client', None) # Ensure client is reset
    assert configure_client() == False
    captured = capsys.readouterr()
    assert "GOOGLE_API_KEY not found" in captured.out
    assert gemini_utils.client is None

def test_configure_client_exception(monkeypatch, capsys):
    """Test client configuration when genai.Client() raises an exception."""
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "test_api_key")
    monkeypatch.setattr(gemini_utils, 'client', None) # Ensure client is reset
    with patch('gemini_utils.genai.Client', side_effect=Exception("Config error")):
        assert configure_client() == False
        captured = capsys.readouterr()
        assert "Error configuring Gemini client: Config error" in captured.out
        assert gemini_utils.client is None


# --- Tests for get_available_models ---

@pytest.fixture(autouse=True)
def setup_gemini_utils_for_test(monkeypatch):
    """Clears cache and sets default API key for tests in this module."""
    monkeypatch.setattr(gemini_utils, 'FETCHED_MODELS_CACHE', [])
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "dummy_api_key_for_tests")
    # Client configuration is typically handled by mock_gemini_client or specific test setups

def test_get_available_models_client_not_configured(monkeypatch, capsys):
    # This test ensures that if configure_client() was not called or failed,
    # and thus gemini_utils.client is None, it handles it gracefully.
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key") # API key exists
    monkeypatch.setattr(gemini_utils, 'client', None) # But client is not configured

    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME] # Should return default
    captured = capsys.readouterr()
    assert "Gemini client not configured" in captured.out

def test_get_available_models_sdk_success(mock_gemini_client, monkeypatch):
    # mock_gemini_client fixture (from conftest) patches genai.Client
    # and calls configure_client(), so gemini_utils.client is the mock.
    # We just need to ensure GOOGLE_API_KEY is set for configure_client to "succeed".
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    # The mock_gemini_client fixture ensures gemini_utils.client is the mock.

    # Conftest mock provides: GEMINI_UTILS_DEFAULT_MODEL_NAME and "models/gemini-1.0-pro"
    expected_models = sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, "models/gemini-1.0-pro"])
    models = get_available_models()
    assert sorted(models) == expected_models
    mock_gemini_client.models.list.assert_called_once()

def test_get_available_models_sdk_no_suitable_models(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    # Override the conftest mock for models.list
    mock_gemini_client.models.list.return_value = [
        MagicMock(name="models/unsupported-model", supported_actions=['embedContent'])
    ]
    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME] # Fallback to default
    captured = capsys.readouterr()
    assert "No suitable 'gemini' models found via SDK" in captured.out

def test_get_available_models_sdk_fails(mock_gemini_client, monkeypatch, capsys):
    # Test when the SDK call itself fails (e.g., network error, API error)
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.list.side_effect = Exception("SDK Network Error")

    models = get_available_models()
    assert models == [GEMINI_UTILS_DEFAULT_MODEL_NAME] # Fallback to default
    captured = capsys.readouterr()
    assert "Error fetching models via new SDK: SDK Network Error" in captured.out
    assert "Falling back to default" in captured.out

def test_get_available_models_caching(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    expected_models = sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, "models/gemini-1.0-pro"])

    # First call
    models1 = get_available_models()
    assert sorted(models1) == expected_models
    mock_gemini_client.models.list.assert_called_once()
    first_call_out = capsys.readouterr().out
    assert "Fetching available models via new SDK" in first_call_out
    assert "Fetched and sorted available models" in first_call_out


    # Second call - should use cache
    models2 = get_available_models()
    assert sorted(models2) == expected_models
    mock_gemini_client.models.list.assert_called_once() # Still once
    second_call_out = capsys.readouterr().out
    assert "Using cached model list" in second_call_out
    assert "Fetching available models via new SDK" not in second_call_out

    # Third call - force refresh
    models3 = get_available_models(force_refresh=True)
    assert sorted(models3) == expected_models
    assert mock_gemini_client.models.list.call_count == 2 # Called again
    third_call_out = capsys.readouterr().out
    assert "Fetching available models via new SDK" in third_call_out

def test_get_available_models_default_model_added(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)

    other_model_name_prefixed = "models/gemini-other-model" # Already prefixed
    mock_model_other = MagicMock(supported_actions=['generateContent'])
    mock_model_other.name = other_model_name_prefixed # Set attribute directly

    assert other_model_name_prefixed != GEMINI_UTILS_DEFAULT_MODEL_NAME # Sanity check
    mock_gemini_client.models.list.return_value = [mock_model_other]

    models = get_available_models()
    # GEMINI_UTILS_DEFAULT_MODEL_NAME is already prefixed
    assert GEMINI_UTILS_DEFAULT_MODEL_NAME in models
    assert other_model_name_prefixed in models
    assert sorted(models) == sorted([GEMINI_UTILS_DEFAULT_MODEL_NAME, other_model_name_prefixed])


# --- Tests for generate_response_stream ---

def test_generate_response_stream_success(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    prompt = "Test prompt"
    # GEMINI_UTILS_DEFAULT_MODEL_NAME is already prefixed.
    model_name_to_test = GEMINI_UTILS_DEFAULT_MODEL_NAME

    stream_data = list(generate_response_stream(prompt, model_name_to_test))

    mock_gemini_client.models.generate_content.assert_called_once_with(
        model=model_name_to_test, contents=prompt, stream=True
    )
    assert len(stream_data) == 3 # 2 chunks + end_stream from conftest mock
    assert json.loads(stream_data[0].split("data: ")[1]) == {"text": "Test response chunk 1."}
    assert json.loads(stream_data[1].split("data: ")[1]) == {"text": "Test response chunk 2."}
    assert json.loads(stream_data[2].split("data: ")[1]) == {"end_stream": True}

def test_generate_response_stream_api_error(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    # Configure generate_content (for streaming) to raise an error
    mock_gemini_client.models.generate_content.side_effect = Exception("API Error")

    stream_data = list(generate_response_stream("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME))

    assert len(stream_data) == 1
    error_payload = json.loads(stream_data[0].split("data: ")[1])
    assert "error" in error_payload
    assert "An error occurred during generation: API Error" in error_payload["error"]

def test_generate_response_stream_no_text_in_chunk(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_chunk_with_text = MagicMock(text="Hello")
    mock_chunk_no_text = MagicMock(text=None)
    # Override generate_content to return these specific chunks for a streaming call
    def side_effect_for_no_text_chunk(*args, **kwargs):
        if kwargs.get('stream'):
            return iter([mock_chunk_with_text, mock_chunk_no_text])
        # Fallback for non-streaming if needed by other tests using this specific mock instance
        return MagicMock(text="Fallback non-stream summary")
    mock_gemini_client.models.generate_content.side_effect = side_effect_for_no_text_chunk

    stream_data = list(generate_response_stream("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME))

    assert len(stream_data) == 2 # 1 data chunk with "Hello" + end_stream
    assert json.loads(stream_data[0].split("data: ")[1]) == {"text": "Hello"}
    assert json.loads(stream_data[1].split("data: ")[1]) == {"end_stream": True}


# --- Tests for generate_summary ---

def test_generate_summary_success(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    prompt = "Summarize this"
    model_name_to_test = GEMINI_UTILS_DEFAULT_MODEL_NAME # Already prefixed

    summary = generate_summary(prompt, model_name_to_test)

    # The conftest mock for generate_content (non-streaming) should be called.
    mock_gemini_client.models.generate_content.assert_called_once_with(
        model=model_name_to_test, contents=prompt # stream=False is default
    )
    assert summary == "Test summary response."

def test_generate_summary_api_error(mock_gemini_client, monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    # Configure generate_content (for non-streaming) to raise an error
    def side_effect_for_summary_error(*args, **kwargs):
        if not kwargs.get('stream'): # Non-streaming
            raise Exception("Summary API Error")
        # Fallback for streaming if any other test uses this specific mock instance by mistake
        return iter([MagicMock(text="Fallback stream chunk")])
    mock_gemini_client.models.generate_content.side_effect = side_effect_for_summary_error

    with pytest.raises(Exception, match="Summary API Error"):
        generate_summary("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME)

def test_generate_summary_client_not_configured(monkeypatch):
    monkeypatch.setattr(gemini_utils, 'client', None)
    with pytest.raises(ValueError, match="Gemini client not configured"):
        generate_summary("prompt", GEMINI_UTILS_DEFAULT_MODEL_NAME)

def test_get_available_models_sdk_error_prints_fallback_message(mock_gemini_client, monkeypatch, capsys):
    monkeypatch.setattr(gemini_utils, 'GOOGLE_API_KEY', "fake_key")
    monkeypatch.setattr(gemini_utils, 'client', mock_gemini_client)
    mock_gemini_client.models.list.side_effect = Exception("Custom SDK Error")

    # No need to mock requests.get as the fallback was removed
    get_available_models()

    captured = capsys.readouterr()
    assert "Error fetching models via new SDK: Custom SDK Error" in captured.out
    assert "Falling back to default" in captured.out
