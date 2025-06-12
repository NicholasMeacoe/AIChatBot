import pytest
import json
from unittest.mock import patch, MagicMock, ANY
from io import BytesIO

from flask import current_app
from config import DEFAULT_MODEL_NAME, FREE_TIER_LIMITS
import config as app_config # To monkeypatch GOOGLE_API_KEY for specific tests

# --- Tests for / (index) ---
@patch('routes.main_routes.get_distinct_chat_dates')
@patch('routes.main_routes.get_chat_history')
@patch('routes.main_routes.get_available_models')
def test_index_route_no_date(mock_get_models, mock_get_history, mock_get_dates, client):
    mock_get_dates.return_value = ["2023-01-01", "2023-01-02"]
    mock_get_models.return_value = [DEFAULT_MODEL_NAME, "gemini-pro"]

    response = client.get('/')
    assert response.status_code == 200

    mock_get_dates.assert_called_once()
    mock_get_models.assert_called_once()
    mock_get_history.assert_not_called()

    assert b"Chat History" in response.data
    assert DEFAULT_MODEL_NAME.encode() in response.data
    assert str(FREE_TIER_LIMITS['max_context_items']).encode() in response.data
    assert str(FREE_TIER_LIMITS['max_total_context_chars']).encode() in response.data


@patch('routes.main_routes.get_distinct_chat_dates')
@patch('routes.main_routes.get_chat_history')
@patch('routes.main_routes.get_available_models')
def test_index_route_with_date(mock_get_models, mock_get_history, mock_get_dates, client):
    mock_get_dates.return_value = ["2023-01-01"]
    mock_get_models.return_value = [DEFAULT_MODEL_NAME]
    mock_history_data = [{"user_message": "Hello", "bot_response": "Hi", "timestamp": "2023-01-01 10:00:00"}]
    mock_get_history.return_value = mock_history_data

    response = client.get('/?date=2023-01-01')
    assert response.status_code == 200
    mock_get_history.assert_called_once_with("2023-01-01")
    assert b"Hello" in response.data


# --- Tests for /chat ---
# Patching where functions are looked up in main_routes.py
@patch('routes.main_routes.save_chat_history')
@patch('routes.main_routes.generate_response_stream') # This is gemini_utils.generate_response_stream
@patch('routes.main_routes.process_context_path')
@patch('routes.main_routes.fetch_and_process_url')
@patch('routes.main_routes.get_available_models')
def test_chat_endpoint_basic_message(mock_get_models, mock_fetch_url, mock_process_path, mock_gen_stream, mock_save_history, client, mock_gemini_client):
    # mock_gemini_client ensures that if generate_response_stream was not patched, its internal calls would be mocked.
    # Here, we patch generate_response_stream itself for more direct control.
    mock_get_models.return_value = [DEFAULT_MODEL_NAME]
    mock_gen_stream.return_value = iter([
        f"data: {json.dumps({'text': 'Response chunk 1 '})}\n\n",
        f"data: {json.dumps({'text': 'chunk 2.'})}\n\n",
        f"data: {json.dumps({'end_stream': True})}\n\n"
    ])

    payload = {"message": "Test message", "model_name": DEFAULT_MODEL_NAME, "active_context": []}
    response = client.post('/chat', json=payload)

    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'

    streamed_content = response.get_data(as_text=True)
    # A more robust check for SSE data might parse each event
    assert "data: {\"text\": \"Response chunk 1 \"}\n\n" in streamed_content
    assert "data: {\"text\": \"chunk 2.\"}\n\n" in streamed_content
    assert "data: {\"end_stream\": true}\n\n" in streamed_content

    mock_gen_stream.assert_called_once_with("Test message", DEFAULT_MODEL_NAME)
    # The combined bot response is "Response chunk 1 chunk 2."
    mock_save_history.assert_called_once_with("Test message", "Response chunk 1 chunk 2.", [])
    mock_process_path.assert_not_called()
    mock_fetch_url.assert_not_called()

@patch('routes.main_routes.save_chat_history')
@patch('routes.main_routes.generate_response_stream')
@patch('routes.main_routes.process_context_path')
@patch('routes.main_routes.fetch_and_process_url') # Mock even if not used to prevent actual calls
@patch('routes.main_routes.get_available_models')
def test_chat_endpoint_with_file_context(mock_get_models, mock_fetch_url, mock_process_path, mock_gen_stream, mock_save_history, client):
    mock_get_models.return_value = [DEFAULT_MODEL_NAME]
    file_context_info = {"original": "file.txt", "status": "ok", "path_type": "file", "actual_path": "/path/file.txt", "message": "File processed"}
    mock_process_path.return_value = ("File context. ", None, file_context_info)
    mock_gen_stream.return_value = iter([f"data: {json.dumps({'text': 'Reply.'})}\n\n", f"data: {json.dumps({'end_stream': True})}\n\n"])

    payload = {
        "message": "User msg",
        "active_context": ["file.txt"],
        "model_name": DEFAULT_MODEL_NAME
    }
    client.post('/chat', json=payload)

    mock_process_path.assert_called_once_with("file.txt")
    mock_gen_stream.assert_called_once_with("File context. User msg", DEFAULT_MODEL_NAME)
    mock_save_history.assert_called_once_with("User msg", "Reply.", [file_context_info])
    mock_fetch_url.assert_not_called()

@patch('routes.main_routes.save_chat_history')
@patch('routes.main_routes.generate_response_stream')
@patch('routes.main_routes.process_context_path')
@patch('routes.main_routes.fetch_and_process_url')
@patch('routes.main_routes.get_available_models')
def test_chat_endpoint_context_error_handling(mock_get_models, mock_fetch_url, mock_process_path, mock_gen_stream, mock_save_history, client):
    mock_get_models.return_value = [DEFAULT_MODEL_NAME]
    good_context_info = {"original": "good.txt", "status": "ok", "path_type": "file", "message": "Processed good.txt"}
    bad_context_info = {"original": "bad.url", "status": "error", "path_type": "url", "message": "URL fetch error"}

    mock_process_path.return_value = ("Good context. ", None, good_context_info)
    mock_fetch_url.return_value = ("", "URL fetch error", bad_context_info) # error string in 2nd pos

    mock_gen_stream.return_value = iter([f"data: {json.dumps({'text': 'Response based on good context.'})}\n\n", f"data: {json.dumps({'end_stream': True})}\n\n"])

    payload = {
        "message": "Check this",
        "active_context": ["good.txt", "bad.url"],
        "model_name": DEFAULT_MODEL_NAME
    }
    response = client.post('/chat', json=payload)
    streamed_content = response.get_data(as_text=True)

    assert f"data: {json.dumps({'context_error': {'item': 'bad.url', 'message': 'URL fetch error'}})}\n\n" in streamed_content
    assert f"data: {json.dumps({'text': 'Response based on good context.'})}\n\n" in streamed_content

    # Prompt includes error message from failed context item
    expected_prompt = "Good context. Error processing context for bad.url: URL fetch error. Check this"
    mock_gen_stream.assert_called_once_with(expected_prompt, DEFAULT_MODEL_NAME)

    expected_db_context_info = [good_context_info, bad_context_info]
    mock_save_history.assert_called_once_with("Check this", "Response based on good context.", expected_db_context_info)


def test_chat_endpoint_no_message_no_context(client):
    payload = {"message": "", "active_context": [], "model_name": DEFAULT_MODEL_NAME}
    response = client.post('/chat', json=payload)
    assert response.status_code == 400
    assert "No message or context provided" in response.json['error']

@patch('routes.main_routes.get_available_models', return_value=["other_model"])
def test_chat_endpoint_invalid_model(mock_get_avail_models, client):
    payload = {"message": "Hi", "model_name": "invalid_model_name_chat", "active_context": []}
    response = client.post('/chat', json=payload)
    assert response.status_code == 400
    assert "Invalid model selected" in response.json['error']

def test_chat_no_api_key(client, monkeypatch):
    monkeypatch.setattr(app_config, 'GOOGLE_API_KEY', None)
    # Ensure gemini_utils reflects this if it caches or re-reads
    monkeypatch.setattr('gemini_utils.GOOGLE_API_KEY', None)
    # This test assumes that the API key check in the route is effective.
    # The route calls configure_gemini_api which sets a global client.
    # If client is None, it should error.
    with patch('gemini_utils.client', None): # Ensure client is None for the check in /chat
        payload = {"message": "test", "model_name": DEFAULT_MODEL_NAME, "active_context": []}
        response = client.post('/chat', json=payload)
        assert response.status_code == 500, f"Response: {response.json}"
        assert "API Key not configured" in response.json['error']


# --- Tests for /fetch_history ---
@patch('routes.main_routes.get_chat_history')
def test_fetch_history_all(mock_get_chat_history, client):
    mock_data = [{"user_message": "msg1", "bot_response": "res1", "timestamp": "2023-01-01 12:00:00"}]
    mock_get_chat_history.return_value = mock_data

    response = client.get('/fetch_history')
    assert response.status_code == 200
    assert response.json == {'history': mock_data}
    mock_get_chat_history.assert_called_once_with(None)

@patch('routes.main_routes.get_chat_history')
def test_fetch_history_by_date(mock_get_chat_history, client):
    mock_data = [{"user_message": "msg2", "bot_response": "res2", "timestamp": "2023-01-02 13:00:00"}]
    mock_get_chat_history.return_value = mock_data

    response = client.get('/fetch_history?date=2023-01-02')
    assert response.status_code == 200
    assert response.json == {'history': mock_data}
    mock_get_chat_history.assert_called_once_with("2023-01-02")


# --- Tests for /delete_history/<date_str> ---
@patch('routes.main_routes.delete_history_by_date')
def test_delete_history_success(mock_delete, client):
    mock_delete.return_value = 5
    response = client.delete('/delete_history/2023-01-01')
    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['deleted_count'] == 5
    assert response.json['message'] == "History for 2023-01-01 deleted."
    mock_delete.assert_called_once_with("2023-01-01")

def test_delete_history_invalid_date_format(client):
    response = client.delete('/delete_history/invalid-date')
    assert response.status_code == 400
    assert "Invalid date format" in response.json['error']

@patch('routes.main_routes.delete_history_by_date')
def test_delete_history_no_rows_deleted(mock_delete, client):
    mock_delete.return_value = 0 # Simulate 0 rows deleted
    response = client.delete('/delete_history/2023-01-01')
    assert response.status_code == 200 # Still success, but indicates 0 deleted
    assert response.json['success'] is True # True because operation was attempted
    assert response.json['deleted_count'] == 0
    assert "No history found to delete" in response.json['message']
    mock_delete.assert_called_once_with("2023-01-01")
