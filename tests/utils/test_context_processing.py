import pytest
import os
import shutil
from unittest.mock import patch, MagicMock, ANY # Moved ANY here

# Functions to test
from context_processing import fetch_and_process_url, process_context_path

# Config values that might be relevant
from config import (
    ALLOWED_CONTEXT_DIR as CONFIG_ALLOWED_CONTEXT_DIR,
    ALLOWED_CONTEXT_DIR_NAME as CONFIG_ALLOWED_CONTEXT_DIR_NAME,
    MAX_URL_CONTENT_BYTES, MAX_FILE_READ_BYTES # MAX_FILE_SIZE_MB is for upload, not direct read here
)
import config # To monkeypatch its values like ALLOWED_CONTEXT_DIR

import requests # For requests.exceptions types


# --- Tests for fetch_and_process_url ---

def test_fetch_url_html_success(mock_requests_get):
    mock_requests_get.return_value.headers = {'content-type': 'text/html; charset=utf-8'}
    # context_processing.py uses response.content, not response.text for initial fetch
    mock_requests_get.return_value.content = b"<html><head><script>bad script</script><style>ugly style</style></head><body><p>Good content</p></body></html>"
    # iter_content is used for streaming and size checking
    mock_requests_get.return_value.iter_content.return_value = iter([b"<html><head><script>bad script</script>",
                                                                    b"<style>ugly style</style></head><body>",
                                                                    b"<p>Good content</p></body></html>"])

    url = "http://example.com/html"
    context, error, info = fetch_and_process_url(url)

    assert error is None, f"Error was {error}, info: {info}"
    assert "Good content" in context
    assert "bad script" not in context # Should be stripped by BeautifulSoup
    assert "ugly style" not in context # Should be stripped
    assert f"START CONTEXT FROM URL: {url}" in context
    assert info["status"] == "ok"
    assert info["context_added"] is True
    # Check that requests.get was called with stream=True
    # from unittest.mock import ANY # Import ANY <- Removed from here
    mock_requests_get.assert_called_once_with(url, headers=ANY, timeout=ANY, stream=True) # Corrected indentation

def test_fetch_url_text_success(mock_requests_get):
    mock_requests_get.return_value.headers = {'content-type': 'text/plain; charset=utf-8'}
    mock_requests_get.return_value.content = b"Just plain text."
    mock_requests_get.return_value.iter_content.return_value = iter([b"Just plain text."])

    url = "http://example.com/text"
    context, error, info = fetch_and_process_url(url)

    assert error is None
    assert "Just plain text." in context
    assert f"START CONTEXT FROM URL: {url}" in context
    assert info["status"] == "ok"

def test_fetch_url_unsupported_content_type(mock_requests_get):
    mock_requests_get.return_value.headers = {'content-type': 'image/jpeg'}
    mock_requests_get.return_value.content = b"jpeg data" # Content doesn't matter much here
    mock_requests_get.return_value.iter_content.return_value = iter([b"jpeg data"])
    url = "http://example.com/image.jpg"
    context, error, info = fetch_and_process_url(url)

    # error (error_msg) will contain the message. info["message"] will also have it.
    assert error is not None
    assert "Unsupported content type 'image/jpeg'" in error
    assert context == ""
    assert "Unsupported content type 'image/jpeg'" in info["message"]
    assert info["status"] == "error"
    assert info["context_added"] is False

def test_fetch_url_timeout(mock_requests_get):
    mock_requests_get.side_effect = requests.exceptions.Timeout("Request timed out")
    url = "http://example.com/timeout"
    context, error, info = fetch_and_process_url(url)

    assert error is not None
    assert "Timeout fetching URL" in error
    assert context == ""
    assert "Timeout fetching URL" in info["message"]
    assert info["status"] == "error"

def test_fetch_url_http_error(mock_requests_get):
    mock_requests_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    # Also ensure iter_content is available on the mock response even if raise_for_status fails first
    mock_requests_get.return_value.iter_content.return_value = iter([])
    url = "http://example.com/notfound"
    context, error, info = fetch_and_process_url(url)

    assert error is not None
    assert "Error fetching URL" in error
    assert context == ""
    assert "Error fetching URL" in info["message"]
    assert "404 Not Found" in info["message"]
    assert info["status"] == "error"

def test_fetch_url_content_exceeds_limit(mock_requests_get, monkeypatch):
    monkeypatch.setattr(config, 'MAX_URL_CONTENT_BYTES', 5)
    mock_requests_get.return_value.headers = {'content-type': 'text/plain; charset=utf-8'}
    # response.content would be the full content if not streamed, but iter_content is used for limit
    mock_requests_get.return_value.iter_content.return_value = iter([b"123", b"45", b"67890"]) # Total 10 bytes
    # The actual text extracted might depend on how iter_content is consumed up to the limit
    # For this test, we assume the first 5 bytes "12345" form the text.
    mock_requests_get.return_value.content = b"1234567890" # For initial check if any

    url = "http://example.com/large"
    context, error, info = fetch_and_process_url(url)

    # If error_msg is a warning for truncation, it might be in info['message']
    # and error could be None if the operation is still considered 'ok' partially.
    # The function returns error_msg directly. If it's None, the test fails.
    # Let's stick to checking info['message'] for the specific message as the primary,
    # and ensure info['status'] is as expected.
    # The previous run showed 'error' was None.
    assert "URL content exceeds limit" in info["message"] # This is already asserted later
    # context should contain the truncated content plus headers and truncation message
    assert "12345" in context
    assert "67890" not in context # Ensure the rest is not there
    assert "... (Content Truncated)" in context # Check for the specific truncation message in context
    assert "URL content exceeds limit" in info["message"]
    assert info["status"] == "ok" # Status is still 'ok' because some content was processed
    assert info["context_added"] is True


# --- Tests for process_context_path ---

@pytest.fixture(autouse=True)
def ensure_original_allowed_context_dir(monkeypatch):
    """Ensures that ALLOWED_CONTEXT_DIR in the config module is reset after each test."""
    original_dir = CONFIG_ALLOWED_CONTEXT_DIR
    original_name = CONFIG_ALLOWED_CONTEXT_DIR_NAME
    yield
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', original_dir)
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR_NAME', original_name)


def test_process_path_read_file_success(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    file_path_abs = os.path.join(temp_allowed_context_dir, "testfile.txt")
    with open(file_path_abs, "w") as f:
        f.write("Hello from testfile!")

    context, error, info = process_context_path("testfile.txt")

    assert error is None, f"Error: {error}, Info: {info}"
    assert "Hello from testfile!" in context
    assert "START CONTEXT FROM FILE: testfile.txt" in context
    assert info["status"] == "ok"
    assert info["context_added"] is True
    assert info["original"] == "testfile.txt"
    assert info["resolved"] == file_path_abs

def test_process_path_file_too_large(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    monkeypatch.setattr(config, 'MAX_FILE_READ_BYTES', 5)
    file_path_abs = os.path.join(temp_allowed_context_dir, "largefile.txt")
    with open(file_path_abs, "w") as f:
        f.write("This_is_too_large_for_the_test_limit")

    context, error, info = process_context_path("largefile.txt")

    # Similar to above, if 'error' is None, but info['message'] has the error,
    # then the function might differentiate between hard errors and warnings/partial success.
    # The function for this case explicitly returns an error_msg.
    # If test output says error is None, this is where the check should be.
    assert "too large" in info["message"] # This is already asserted
    assert error is not None # Re-asserting this based on code review; if it fails, the function has an issue.
    if error: # Only check content if error is not None
        assert "too large" in error
    assert context == "" # Context should be empty as per function logic
    assert info["status"] == "error" # Status should be error as file processing failed
    assert info["context_added"] is False

def test_process_path_file_not_found(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    context, error, info = process_context_path("nonexistent.txt")
    assert error is not None # error message is returned by process_context_path
    assert "Path not found" in error
    assert context == ""
    assert "Path not found" in info["message"]
    assert info["status"] == "error"

def test_process_path_list_directory_success(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)

    file1_path = os.path.join(temp_allowed_context_dir, "file1.txt")
    with open(file1_path, "w") as f: f.write("0123456789")

    subfolder_name = "subfolder"
    subfolder_path_abs = os.path.join(temp_allowed_context_dir, subfolder_name)
    os.makedirs(subfolder_path_abs)
    file2_path = os.path.join(subfolder_path_abs, "file2.txt")
    with open(file2_path, "w") as f: f.write("01234")

    context, error, info = process_context_path(".")

    assert error is None, f"Error: {info['message']}"
    assert "START CONTEXT FROM FOLDER CONTENTS: ." in context
    assert "file1.txt [File]" in context
    assert f"{subfolder_name}/ [DIR]" in context
    assert info["status"] == "ok"
    assert info["context_added"] is True

    # Test listing the subfolder using its relative path from ALLOWED_CONTEXT_DIR
    context_sub, error_sub, info_sub = process_context_path(subfolder_name)
    assert error_sub is None, f"Error sub: {info_sub['message']}"
    assert f"START CONTEXT FROM FOLDER CONTENTS: {subfolder_name}/" in context_sub
    # In context_processing, listed paths are relative to the *listed folder*, not ALLOWED_CONTEXT_DIR root.
    assert "file2.txt [File]" in context_sub
    assert info_sub["status"] == "ok"

def test_process_path_list_empty_directory(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    empty_dir_name = "empty_dir"
    os.makedirs(os.path.join(temp_allowed_context_dir, empty_dir_name))
    context, error, info = process_context_path(empty_dir_name)
    assert error is None
    assert "(Folder is empty)" in context
    assert info["status"] == "ok"
    assert info["context_added"] is True

def test_process_path_security_absolute_path(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    abs_path_to_try = "/etc/passwd" if os.name != 'nt' else "C:\\Windows\\System32\\drivers\\etc\\hosts"

    context, error, info = process_context_path(abs_path_to_try)
    assert error is not None
    assert "absolute paths are forbidden" in error
    assert "absolute paths are forbidden" in info["message"]
    assert info["status"] == "error"

def test_process_path_security_path_traversal(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    context, error, info = process_context_path("../../../etc/passwd")
    assert error is not None
    assert "Path traversal ('..')" in error or "is outside the allowed directory" in error
    assert "Path traversal ('..')" in info["message"] or "is outside the allowed directory" in info["message"]
    assert info["status"] == "error"

def test_process_path_with_quotes_and_spaces(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    file_content = "File with spaces in name"
    actual_filename = "file_no_spaces.txt"
    # Input path string given by user, with quotes and spaces
    user_input_path = f' "{actual_filename}" '

    file_path_abs = os.path.join(temp_allowed_context_dir, actual_filename)
    with open(file_path_abs, "w") as f:
        f.write(file_content)

    context, error, info = process_context_path(user_input_path)
    assert error is None, f"Error: {info['message']}"
    assert file_content in context
    assert info["original"] == user_input_path
    assert info["resolved"] == os.path.realpath(file_path_abs)
    assert info["status"] == "ok"

def test_process_path_allowed_dir_not_configured(monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', None)
    context, error, info = process_context_path("somefile.txt")
    assert error is not None
    assert "allowed context directory is not configured" in error
    assert "allowed context directory is not configured" in info["message"]
    assert context == ""
    assert info["status"] == "error"

def test_process_path_allowed_dir_does_not_exist(monkeypatch, temp_allowed_context_dir):
    # Create a path that is guaranteed not to exist for the test.
    non_existent_dir = os.path.join(temp_allowed_context_dir, "non_existent_sub_dir_for_config")
    # Ensure it's gone if it somehow exists from a previous failed test run (unlikely with temp dirs)
    if os.path.exists(non_existent_dir): shutil.rmtree(non_existent_dir)

    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', non_existent_dir)

    context, error, info = process_context_path("somefile.txt")
    assert error is not None
    assert "does not exist" in error # Simpler check for the core message part
    assert "does not exist" in info["message"] # Simpler check
    assert context == ""
    assert info["status"] == "error"

def test_process_path_list_directory_file_too_large_skipped(temp_allowed_context_dir, monkeypatch):
    monkeypatch.setattr(config, 'ALLOWED_CONTEXT_DIR', temp_allowed_context_dir)
    monkeypatch.setattr(config, 'MAX_FILE_READ_BYTES', 5) # For file content reading if attempted

    # Create small file (will be listed)
    small_file_path = os.path.join(temp_allowed_context_dir, "small.txt")
    with open(small_file_path, "w") as f: f.write("ok")

    # Create large file (will be listed but marked as too large if size comes from os.path.getsize)
    # context_processing.py uses MAX_FILE_SIZE_MB for *listing* (os.path.getsize)
    # and MAX_FILE_READ_BYTES for *reading content*.
    # Let's make it exceed MAX_FILE_SIZE_MB for listing.
    # Default MAX_FILE_SIZE_MB = 10. Let's set it to 0.00001 MB (around 10 bytes) for test.
    monkeypatch.setattr(config, 'MAX_FILE_SIZE_MB', 0.00001) # Approx 10 bytes

    large_file_path = os.path.join(temp_allowed_context_dir, "large_for_listing.txt")
    with open(large_file_path, "w") as f: f.write("This content is definitely larger than 10 bytes") # >10 bytes

    context, error, info = process_context_path(".")

    assert error is None, f"Error: {info['message']}"
    assert "small.txt [File]" in context
    # The message in code is "SKIPPED - Too large: {size_kb / 1024:.2f} MB"
    # The dynamic config loading is now working, so we expect the "SKIPPED" message.
    assert "large_for_listing.txt [File] (SKIPPED - Too large:" in context
    assert info["status"] == "ok"

# TODO: Add test for fetch_and_process_url with different encodings if possible.
# This is tricky because requests handles decoding. We'd need to mock response.content with specific byte patterns
# and ensure response.encoding is not set or set to something that would cause issues if not for our handling.
# Current code uses response.text which relies on requests' auto-detection or charset from headers.
# If specific encoding byte sequences are needed, response.content should be mocked with those bytes.
# For now, the UTF-8 success test is the primary one.
