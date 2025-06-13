import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

# Function to test
from pdf_utils import convert_images_to_pdf, PDFConversionError
# Import the custom TesseractNotFoundError from pdf_utils to test against it
from pdf_utils import TesseractNotFoundError as PdfUtilsTesseractNotFoundError
from config import ALLOWED_PDF_EXTENSIONS

# Import pytesseract's actual error to simulate it being raised
from pytesseract import TesseractNotFoundError as PytesseractOriginalNotFoundError


# Helper to create a mock file object (like Flask's FileStorage)
def create_mock_image_file(filename="test.jpg", content=b"fake_jpeg_bytes", read_error=None, verify_error=None, pil_format='JPEG', is_empty=False):
    mock_file = MagicMock(spec=['filename', 'read', 'seek'])
    mock_file.filename = filename

    if read_error:
        mock_file.read.side_effect = read_error
    elif is_empty:
        mock_file.read.return_value = b""
    else:
        mock_file.read.return_value = content

    mock_image_instance = MagicMock(spec=['verify', 'format', 'close']) # Added 'close'
    mock_image_instance.format = pil_format

    if verify_error:
        mock_image_instance.verify.side_effect = verify_error
    else:
        mock_image_instance.verify.return_value = None

    return mock_file, mock_image_instance


@patch('pdf_utils.Image')
def test_convert_images_no_ocr_success(MockPILImage, mock_img2pdf_convert): # mock_img2pdf_convert from conftest
    mock_file1, mock_img_instance1 = create_mock_image_file("img1.jpg")
    mock_file2, mock_img_instance2 = create_mock_image_file("img2.jpeg")

    # Image.open should return our mocked image instances.
    # It's called once for validation (verify) and once for processing if OCR.
    # For non-OCR, it's called for validation. The bytes are passed to img2pdf.
    MockPILImage.open.side_effect = [mock_img_instance1, mock_img_instance2]

    expected_pdf_bytes = b"converted_pdf_no_ocr"
    mock_img2pdf_convert.return_value = expected_pdf_bytes # Fixture provides the mock

    files = [mock_file1, mock_file2]
    pdf_stream = convert_images_to_pdf(files, ocr_enabled=False)

    assert pdf_stream.getvalue() == expected_pdf_bytes
    assert MockPILImage.open.call_count == 2
    mock_img_instance1.verify.assert_called_once()
    mock_img_instance2.verify.assert_called_once()
    # img2pdf.convert is called with a list of bytes
    mock_img2pdf_convert.assert_called_once_with([b"fake_jpeg_bytes", b"fake_jpeg_bytes"])


@patch('pdf_utils.Image')
@patch('pdf_utils.PdfMerger')
def test_convert_images_with_ocr_success(MockPdfMerger, MockPILImage, mock_pytesseract): # mock_pytesseract from conftest
    mock_file1, mock_img_instance1 = create_mock_image_file("img1.jpg")
    # For OCR, Image.open is called for initial validation, then again for processing.
    MockPILImage.open.side_effect = [mock_img_instance1, mock_img_instance1]

    ocr_page_bytes = b"searchable_pdf_bytes_from_ocr"
    mock_pytesseract.return_value = ocr_page_bytes # Fixture provides the mock

    mock_merger_instance = MockPdfMerger.return_value
    # Simulate PdfMerger.write writing the OCR'd page bytes to the stream
    def mock_merger_write_effect(output_stream):
        output_stream.write(ocr_page_bytes)
    mock_merger_instance.write.side_effect = mock_merger_write_effect

    files = [mock_file1]
    pdf_stream = convert_images_to_pdf(files, ocr_enabled=True)

    assert pdf_stream.getvalue() == ocr_page_bytes
    # PIL.Image.open called for validation, then for pytesseract
    assert MockPILImage.open.call_count == 2
    mock_img_instance1.verify.assert_called_once()
    mock_pytesseract.assert_called_once_with(mock_img_instance1, extension='pdf')
    mock_merger_instance.append.assert_called_once()
    mock_merger_instance.write.assert_called_once()
    mock_merger_instance.close.assert_called_once()


def test_convert_no_files_provided():
    with pytest.raises(PDFConversionError, match="No image files provided"):
        convert_images_to_pdf([])

@patch('pdf_utils.Image') # Still need to mock Image.open if it's called before extension check
def test_convert_invalid_extension(MockPILImage):
    mock_file_txt, _ = create_mock_image_file("doc.txt") # create_mock_image_file sets up .filename
    # No need to configure MockPILImage.open if the extension check happens first
    with pytest.raises(PDFConversionError, match="Invalid file type: doc.txt"):
        convert_images_to_pdf([mock_file_txt])

@patch('pdf_utils.Image')
def test_convert_image_pil_verify_error(MockPILImage):
    mock_file, mock_img_instance = create_mock_image_file("bad.jpg", verify_error=Exception("Verify failed"))
    MockPILImage.open.return_value = mock_img_instance # Image.open succeeds
    with pytest.raises(PDFConversionError, match="Invalid or corrupted image file: bad.jpg"):
        convert_images_to_pdf([mock_file])

@patch('pdf_utils.Image')
def test_convert_image_pil_format_error(MockPILImage):
    # Simulate PIL identifying a non-JPEG format after opening.
    # File extension must be valid to bypass the initial extension check.
    mock_file, mock_img_instance = create_mock_image_file(filename="img.jpg", pil_format='PNG')
    MockPILImage.open.return_value = mock_img_instance
    with pytest.raises(PDFConversionError, match="Invalid image format detected.*Only JPEG allowed"):
        convert_images_to_pdf([mock_file])

@patch('pdf_utils.Image')
def test_convert_image_pil_open_error(MockPILImage):
    # Simulate PIL Image.open itself failing (e.g., file is not an image at all)
    mock_file, _ = create_mock_image_file("not_an_image.jpg")
    MockPILImage.open.side_effect = Exception("Cannot identify image file")
    with pytest.raises(PDFConversionError, match="Invalid or corrupted image file: not_an_image.jpg"):
        convert_images_to_pdf([mock_file])

@patch('pdf_utils.Image')
def test_convert_empty_file_content(MockPILImage):
    mock_file, _ = create_mock_image_file("empty.jpg", is_empty=True)
    # Image.open on empty bytes might raise an error.
    MockPILImage.open.side_effect = Exception("PIL cannot open empty file")
    with pytest.raises(PDFConversionError, match="File is empty: empty.jpg|Invalid or corrupted image file: empty.jpg"):
        convert_images_to_pdf([mock_file])


@patch('pdf_utils.Image')
def test_convert_ocr_tesseract_not_found_error(MockPILImage, mock_pytesseract): # mock_pytesseract from conftest
    mock_file1, mock_img_instance1 = create_mock_image_file("img1.jpg")
    MockPILImage.open.side_effect = [mock_img_instance1, mock_img_instance1]

    # Configure the conftest fixture mock to raise the original Pytesseract error
    # Set side_effect to the class, not an instance, to avoid constructor issues.
    mock_pytesseract.side_effect = PytesseractOriginalNotFoundError

    with pytest.raises(PdfUtilsTesseractNotFoundError, match="OCR Error: Tesseract is not installed or not found"):
        convert_images_to_pdf([mock_file1], ocr_enabled=True)

@patch('pdf_utils.Image')
@patch('pdf_utils.PdfMerger') # Mock PdfMerger as it's used in OCR path
def test_convert_ocr_generic_pytesseract_error(MockPdfMerger, MockPILImage, mock_pytesseract):
    mock_file1, mock_img_instance1 = create_mock_image_file("img1.jpg")
    MockPILImage.open.side_effect = [mock_img_instance1, mock_img_instance1]
    mock_pytesseract.side_effect = Exception("Some other OCR lib error")

    with pytest.raises(PDFConversionError, match="An error occurred during OCR processing"):
        convert_images_to_pdf([mock_file1], ocr_enabled=True)


@patch('pdf_utils.Image')
def test_convert_no_ocr_img2pdf_error(MockPILImage, mock_img2pdf_convert): # mock_img2pdf_convert from conftest
    mock_file1, mock_img_instance1 = create_mock_image_file("img1.jpg")
    MockPILImage.open.return_value = mock_img_instance1 # Only one open for non-OCR validation path

    mock_img2pdf_convert.side_effect = Exception("img2pdf internal error from fixture")

    with pytest.raises(PDFConversionError, match="PDF generation failed"):
        convert_images_to_pdf([mock_file1], ocr_enabled=False)

def test_convert_no_valid_files_after_validation(monkeypatch):
    # Test case where all files are invalid and processed_files_data remains empty
    # Mock ALLOWED_PDF_EXTENSIONS to something very specific for this test
    monkeypatch.setattr('pdf_utils.ALLOWED_PDF_EXTENSIONS', {'xyz'})

    mock_file1, _ = create_mock_image_file("img1.jpg") # jpg is not xyz

    with pytest.raises(PDFConversionError, match="No valid JPEG images found to convert after validation|Invalid file type"):
        # The error might be "Invalid file type" if caught early, or "No valid JPEG images" if it passes initial checks
        # but fails deeper validation (which shouldn't happen if extension check is robust).
        # Given the current code, "Invalid file type" is more likely.
        convert_images_to_pdf([mock_file1])

@patch('pdf_utils.Image')
def test_convert_ocr_pytesseract_returns_empty_data(MockPILImage, mock_pytesseract, MockPdfMerger):
    mock_file1, mock_img_instance1 = create_mock_image_file("img.jpg")
    MockPILImage.open.side_effect = [mock_img_instance1, mock_img_instance1]

    mock_pytesseract.return_value = b"" # Simulate pytesseract returning empty bytes

    with pytest.raises(PDFConversionError, match="OCR processing returned empty data for image 1"):
        convert_images_to_pdf([mock_file1], ocr_enabled=True)
