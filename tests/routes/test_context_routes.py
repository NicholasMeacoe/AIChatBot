import pytest
import os
import json
from unittest.mock import patch, MagicMock, ANY

# client, temp_allowed_context_dir, mock_gemini_client are from conftest.py
from config import DEFAULT_MODEL_NAME
import config as app_config # To monkeypatch ALLOWED_CONTEXT_DIR

# Helper to create files in the temp_allowed_context_dir
def create_file_in_temp(base_dir, rel_path, content=""):
    # Ensure rel_path uses os.sep for creation, but tests will compare with URL-like paths
    normalized_rel_path = os.path.join(*rel_path.split('/'))
    full_path = os.path.join(base_dir, normalized_rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    return full_path

# --- Tests for /list_files ---
def test_list_files_empty(client, temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    response = client.get('/context/list_files')
    assert response.status_code == 200
    assert response.json == []

def test_list_files_with_content(client, temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    create_file_in_temp(temp_allowed_context_dir, "file1.txt")
    create_file_in_temp(temp_allowed_context_dir, "folder1/file2.txt")
    create_file_in_temp(temp_allowed_context_dir, "folder1/subfolder/file3.txt")
    os.makedirs(os.path.join(temp_allowed_context_dir, "folder2"), exist_ok=True) # Empty folder

    response = client.get('/context/list_files')
    assert response.status_code == 200
    expected_files = sorted([
        "file1.txt",
        "folder1/file2.txt",
        "folder1/subfolder/file3.txt"
    ])
    assert response.json == expected_files

def test_list_files_allowed_dir_not_exist(client, monkeypatch):
    non_existent_path = "/path/to/nonexistent/dir_for_test_list_files"
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', non_existent_path)
    # context_routes.py uses os.path.isdir to check, so mock that
    with patch('os.path.isdir', return_value=False) as mock_isdir:
        response = client.get('/context/list_files')
        assert response.status_code == 200
        assert response.json == []
        mock_isdir.assert_any_call(non_existent_path)


# --- Tests for /list_folders ---
def test_list_folders_empty(client, temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    response = client.get('/context/list_folders')
    assert response.status_code == 200
    assert response.json == ["./"]

def test_list_folders_with_content(client, temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    os.makedirs(os.path.join(temp_allowed_context_dir, "folder1", "subfolder1"), exist_ok=True)
    os.makedirs(os.path.join(temp_allowed_context_dir, "folder2"), exist_ok=True)
    create_file_in_temp(temp_allowed_context_dir, "file_in_root.txt")

    response = client.get('/context/list_folders')
    assert response.status_code == 200
    expected_folders = sorted([
        "./",
        "folder1/",
        "folder1/subfolder1/",
        "folder2/"
    ])
    # The response.json can have OS-specific separators if not handled in route, ensure comparison is fair
    # The route _should_ convert to forward slashes.
    assert sorted(response.json) == expected_folders


def test_list_folders_allowed_dir_not_exist(client, monkeypatch):
    non_existent_path = "/path/to/nonexistent/dir_for_test_list_folders"
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', non_existent_path)
    with patch('os.path.isdir', return_value=False) as mock_isdir:
        response = client.get('/context/list_folders')
        assert response.status_code == 200
        assert response.json == [] # Route returns empty list
        mock_isdir.assert_any_call(non_existent_path)

# --- Tests for /suggest_path ---
def test_suggest_path_basic(client, temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    create_file_in_temp(temp_allowed_context_dir, "apple.txt")
    os.makedirs(os.path.join(temp_allowed_context_dir, "apricot_folder"), exist_ok=True)
    create_file_in_temp(temp_allowed_context_dir, "banana.txt")

    response = client.get('/context/suggest_path?partial=')
    assert response.status_code == 200
    assert sorted(response.json) == sorted(["apple.txt", "apricot_folder/", "banana.txt"])

    response = client.get('/context/suggest_path?partial=apple')
    assert response.status_code == 200
    assert response.json == ["apple.txt"]

    response = client.get('/context/suggest_path?partial=apr')
    assert response.status_code == 200
    assert response.json == ["apricot_folder/"]

    response = client.get('/context/suggest_path?partial=xyz')
    assert response.status_code == 200
    assert response.json == []

def test_suggest_path_traversal_attempt(client, temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    response = client.get('/context/suggest_path?partial=../')
    assert response.status_code == 200 # Route handles this gracefully
    assert response.json == []

    response = client.get('/context/suggest_path?partial=/etc/passwd')
    assert response.status_code == 200
    assert response.json == []

def test_suggest_path_allowed_dir_not_exist(client, monkeypatch):
    non_existent_path = "/path/to/nonexistent/dir_for_test_suggest"
    monkeypatch.setattr(app_config, 'ALLOWED_CONTEXT_DIR', non_existent_path)
    with patch('os.path.isdir', return_value=False) as mock_isdir:
        response = client.get('/context/suggest_path?partial=a')
        assert response.status_code == 200
        assert response.json == []
        mock_isdir.assert_any_call(non_existent_path)


# --- Tests for /summarize_context ---
# Patching where the functions are LOOKED UP by the route module
@patch('routes.context_routes.process_context_path')
@patch('routes.context_routes.fetch_and_process_url')
@patch('routes.context_routes.generate_summary') # This is gemini_utils.generate_summary
def test_summarize_context_success(mock_generate_summary, mock_fetch_url, mock_process_path, client, mock_gemini_client):
    # mock_gemini_client is active, so if generate_summary was *not* patched, it would use the mocked client.
    # By patching generate_summary directly, we control its output for this route test.

    mock_process_path.return_value = ("File context here.", None, {"status": "ok", "message": "File processed", "path_type": "file", "original": "file.txt"})
    mock_fetch_url.return_value = ("URL context here.", None, {"status": "ok", "message": "URL processed", "path_type": "url", "original": "http://example.com"})
    mock_generate_summary.return_value = "This is the summary."

    payload = {
        "context_items": ["file.txt", "http://example.com"], # Items are strings
        "model_name": DEFAULT_MODEL_NAME
    }
    response = client.post('/context/summarize_context', json=payload)

    assert response.status_code == 200, f"Response: {response.json}"
    assert response.json['summary'] == "This is the summary."
    assert len(response.json['processed_items']) == 2

    mock_process_path.assert_called_once_with("file.txt")
    mock_fetch_url.assert_called_once_with("http://example.com")

    # Check that generate_summary was called with combined context
    mock_generate_summary.assert_called_once()
    # First arg is prompt, second is model_name
    prompt_arg = mock_generate_summary.call_args[0][0]
    model_arg = mock_generate_summary.call_args[0][1]

    assert "File context here." in prompt_arg
    assert "URL context here." in prompt_arg
    assert model_arg == DEFAULT_MODEL_NAME


def test_summarize_context_no_items(client):
    response = client.post('/context/summarize_context', json={"context_items": [], "model_name": DEFAULT_MODEL_NAME})
    assert response.status_code == 400
    assert "Invalid or empty context items list" in response.json['error']

@patch('routes.context_routes.get_available_models', return_value=[DEFAULT_MODEL_NAME]) # Mock model availability check
def test_summarize_context_invalid_model(mock_get_avail_models, client):
    payload = {
        "context_items": ["file.txt"], # Needs at least one item
        "model_name": "invalid-model-for-summary"
    }
    # Need to mock process_context_path as it will be called
    with patch('routes.context_routes.process_context_path', return_value=("Some context", None, {"status":"ok"})):
        response = client.post('/context/summarize_context', json=payload)
        assert response.status_code == 400
        assert "Invalid model selected" in response.json['error']


@patch('routes.context_routes.process_context_path')
@patch('routes.context_routes.generate_summary')
def test_summarize_context_gemini_error(mock_generate_summary, mock_process_path, client):
    mock_process_path.return_value = ("Some file context.", None, {"status":"ok", "path_type":"file", "original":"f.txt"})
    mock_generate_summary.side_effect = Exception("Gemini Down")

    payload = {"context_items": ["f.txt"], "model_name": DEFAULT_MODEL_NAME}
    response = client.post('/context/summarize_context', json=payload)

    assert response.status_code == 500
    assert "Failed to generate summary" in response.json['error']
    assert "Gemini Down" in response.json['details']

@patch('routes.context_routes.process_context_path', return_value=("", "File error", {"status":"error", "message":"File processing error", "path_type":"file", "original":"f.txt"}))
@patch('routes.context_routes.fetch_and_process_url', return_value=("", "URL error", {"status":"error", "message":"URL processing error", "path_type":"url", "original":"http://bad.url"}))
def test_summarize_context_all_items_fail(mock_fetch_url, mock_process_path, client):
    payload = {"context_items": ["f.txt", "http://bad.url"], "model_name": DEFAULT_MODEL_NAME}
    response = client.post('/context/summarize_context', json=payload)

    assert response.status_code == 400
    assert "No context could be gathered from the provided items" in response.json['error']
    assert "details" in response.json
    assert len(response.json["details"]) == 2
    assert response.json["details"][0]["message"] == "File processing error"
    assert response.json["details"][1]["message"] == "URL processing error"

@patch('routes.context_routes.process_context_path')
@patch('routes.context_routes.fetch_and_process_url')
@patch('routes.context_routes.generate_summary')
def test_summarize_context_partial_success(mock_generate_summary, mock_fetch_url, mock_process_path, client):
    mock_process_path.return_value = ("File context here.", None, {"status": "ok", "message": "File processed", "path_type": "file", "original": "goodfile.txt"})
    mock_fetch_url.return_value = ("", "URL error", {"status": "error", "message": "Failed to fetch URL", "path_type": "url", "original": "http://bad.url"})
    mock_generate_summary.return_value = "Summary of file context."

    payload = {
        "context_items": ["goodfile.txt", "http://bad.url"],
        "model_name": DEFAULT_MODEL_NAME
    }
    response = client.post('/context/summarize_context', json=payload)

    assert response.status_code == 200
    assert response.json['summary'] == "Summary of file context."
    assert "Some items could not be processed" in response.json['warnings']
    assert len(response.json['processed_items']) == 2 # Both attempts are recorded
    assert response.json['processed_items'][0]['status'] == 'ok'
    assert response.json['processed_items'][1]['status'] == 'error'

    mock_generate_summary.assert_called_once()
    prompt_arg = mock_generate_summary.call_args[0][0]
    assert "File context here." in prompt_arg
    assert "Failed to fetch URL" not in prompt_arg # Only successful context in prompt
                                                 # Though the current code appends errors to prompt.
                                                 # Let's check current behavior of summarize_context in app.py
                                                 # The current code appends "Error processing ... {item_info['message']}" to prompt
    assert "Error processing URL http://bad.url: Failed to fetch URL" in prompt_arg
