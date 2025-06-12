import pytest
import json
from unittest.mock import patch, MagicMock, call # Added call
from io import BytesIO

# client fixture is from conftest.py
# Import custom exceptions to check against if needed, or just message content
from pdf_utils import PDFConversionError as PdfUtilsPDFConversionError
from pdf_utils import TesseractNotFoundError as PdfUtilsTesseractNotFoundError


# --- Tests for /pdf/convert ---

@patch('routes.pdf_routes.convert_images_to_pdf')
def test_convert_pdf_no_ocr_success(mock_convert_images_to_pdf_util, client):
    mock_pdf_content = b"mock_pdf_bytes_no_ocr"
    # The utility function convert_images_to_pdf returns a BytesIO stream
    mock_convert_images_to_pdf_util.return_value = BytesIO(mock_pdf_content)

    # Simulate file upload. For a single file, Flask test client takes a tuple.
    data = {
        'images': (BytesIO(b"fakeimgbytes1"), 'test1.jpg'),
        'ocr_enabled': 'false' # Form data is typically strings
    }

    response = client.post('/pdf/convert', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    # Check for filename in Content-Disposition, but allow for variations like quoted/unquoted
    assert "attachment;" in response.headers['Content-Disposition']
    assert "filename=converted_images.pdf" in response.headers['Content-Disposition'].replace('"', '')
    assert response.data == mock_pdf_content

    # Check that the utility was called correctly
    mock_convert_images_to_pdf_util.assert_called_once()
    # First argument is the list of files, second is ocr_enabled keyword arg
    assert len(mock_convert_images_to_pdf_util.call_args[0][0]) == 1 # One file
    assert mock_convert_images_to_pdf_util.call_args[0][0][0].filename == 'test1.jpg'
    assert mock_convert_images_to_pdf_util.call_args[1]['ocr_enabled'] is False


@patch('routes.pdf_routes.convert_images_to_pdf')
def test_convert_pdf_with_ocr_success(mock_convert_images_to_pdf_util, client):
    mock_pdf_content = b"mock_pdf_bytes_with_ocr"
    mock_convert_images_to_pdf_util.return_value = BytesIO(mock_pdf_content)

    data = {
        'images': (BytesIO(b"fakeimgbytes_ocr"), 'ocr_test.jpg'),
        'ocr_enabled': 'true'
    }
    response = client.post('/pdf/convert', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert response.data == mock_pdf_content

    mock_convert_images_to_pdf_util.assert_called_once()
    assert len(mock_convert_images_to_pdf_util.call_args[0][0]) == 1
    assert mock_convert_images_to_pdf_util.call_args[0][0][0].filename == 'ocr_test.jpg'
    assert mock_convert_images_to_pdf_util.call_args[1]['ocr_enabled'] is True


@patch('routes.pdf_routes.convert_images_to_pdf')
def test_convert_pdf_multiple_files_success(mock_convert_images_to_pdf_util, client):
    mock_pdf_content = b"mock_pdf_bytes_multiple"
    mock_convert_images_to_pdf_util.return_value = BytesIO(mock_pdf_content)

    # For multiple files, the 'images' key should be a list of file tuples
    data = {
        'images': [
            (BytesIO(b"fakeimgbytes1"), 'test1.jpg'),
            (BytesIO(b"fakeimgbytes2"), 'test2.jpeg')
        ],
        'ocr_enabled': 'false'
    }
    response = client.post('/pdf/convert', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert response.data == mock_pdf_content

    mock_convert_images_to_pdf_util.assert_called_once()
    # Check files passed to the utility
    passed_files_arg = mock_convert_images_to_pdf_util.call_args[0][0]
    assert len(passed_files_arg) == 2
    assert passed_files_arg[0].filename == 'test1.jpg'
    assert passed_files_arg[1].filename == 'test2.jpeg'
    assert mock_convert_images_to_pdf_util.call_args[1]['ocr_enabled'] is False


def test_convert_pdf_no_images_part(client):
    response = client.post('/pdf/convert', data={'ocr_enabled': 'false'}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "No 'images' part" in response.json['error']

def test_convert_pdf_no_files_selected(client):
    # Simulate 'images' field present but no file chosen.
    # This is done by sending a file tuple with an empty filename.
    # Flask/Werkzeug will create a FileStorage object with filename="".
    data = {'images': (BytesIO(b""), '')} # Empty filename
    response = client.post('/pdf/convert', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "No image files selected" in response.json['error']


@patch('routes.pdf_routes.convert_images_to_pdf')
def test_convert_pdf_conversion_error_from_util(mock_convert_images_to_pdf_util, client):
    # Using the imported custom error from pdf_utils for type checking if desired,
    # but here we just check the message.
    mock_convert_images_to_pdf_util.side_effect = PdfUtilsPDFConversionError("Mocked conversion error from util")

    data = {'images': (BytesIO(b"fake_content"), 'test.jpg')} # Need some file data
    response = client.post('/pdf/convert', data=data, content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.json['error'] == "Mocked conversion error from util"

@patch('routes.pdf_routes.convert_images_to_pdf')
def test_convert_pdf_tesseract_not_found_from_util(mock_convert_images_to_pdf_util, client):
    mock_convert_images_to_pdf_util.side_effect = PdfUtilsTesseractNotFoundError("Mocked Tesseract not found from util")

    data = {'images': (BytesIO(b"fake_content"), 'test.jpg'), 'ocr_enabled': 'true'}
    response = client.post('/pdf/convert', data=data, content_type='multipart/form-data')

    assert response.status_code == 500
    assert response.json['error'] == "Mocked Tesseract not found from util"

@patch('routes.pdf_routes.convert_images_to_pdf')
def test_convert_pdf_generic_exception_from_util(mock_convert_images_to_pdf_util, client):
    mock_convert_images_to_pdf_util.side_effect = Exception("Unexpected mock error in util")

    data = {'images': (BytesIO(b"fake_content"), 'test.jpg')}
    response = client.post('/pdf/convert', data=data, content_type='multipart/form-data')

    assert response.status_code == 500
    assert "An unexpected server error occurred" in response.json['error']
    # Optionally, check for the original error message if it's included in production for debugging
    # assert "Unexpected mock error in util" in response.json['details'] # If details were added
