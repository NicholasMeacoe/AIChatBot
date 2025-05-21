import io
import img2pdf
import pytesseract
from PyPDF2 import PdfMerger
from PIL import Image # For image validation and OCR processing
from io import BytesIO # For handling byte streams
from config import ALLOWED_PDF_EXTENSIONS

# Optional: Configure Tesseract path if needed (can be done in config.py)
# from config import TESSERACT_CMD
# if TESSERACT_CMD:
#     pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

class PDFConversionError(Exception):
    """Custom exception for PDF conversion errors."""
    pass

class TesseractNotFoundError(PDFConversionError):
    """Specific exception for when Tesseract is not found."""
    pass

def convert_images_to_pdf(image_files, ocr_enabled=False):
    """
    Converts a list of image file objects (from Flask request.files) to a single PDF.

    Args:
        image_files: A list of file-like objects (e.g., Werkzeug FileStorage).
        ocr_enabled: Boolean indicating whether to perform OCR.

    Returns:
        BytesIO: A stream containing the generated PDF data.

    Raises:
        PDFConversionError: If validation fails, conversion fails, or OCR fails.
        TesseractNotFoundError: If OCR is enabled but Tesseract is not found.
    """
    processed_files_data = [] # Store validated image data (bytes or PIL Image objects)

    if not image_files:
        raise PDFConversionError("No image files provided for conversion.")

    for file in image_files:
        if not file or not file.filename:
             # Skip empty file entries if any
             print("Warning: Skipping empty file entry.")
             continue

        # Basic filename extension check
        if '.' not in file.filename or \
           file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_PDF_EXTENSIONS:
            raise PDFConversionError(f"Invalid file type: {file.filename}. Only {', '.join(ALLOWED_PDF_EXTENSIONS)} allowed.")

        try:
            # Read file into memory
            img_bytes = file.read()
            # Reset stream position in case it's read again (though not strictly necessary here)
            file.seek(0)

            if not img_bytes:
                 raise PDFConversionError(f"File is empty: {file.filename}")

            # Validate image format and integrity using Pillow
            img = Image.open(BytesIO(img_bytes))
            # Check format AFTER opening
            if img.format.lower() not in ['jpeg']: # Pillow uses 'JPEG'
                raise PDFConversionError(f"Invalid image format detected in file: {file.filename}. Only JPEG allowed.")
            img.verify() # Verify image integrity

            # Re-open image after verification for further processing
            # Store PIL image object if OCR is needed, otherwise store bytes for img2pdf
            if ocr_enabled:
                img_for_processing = Image.open(BytesIO(img_bytes))
                processed_files_data.append(img_for_processing)
            else:
                processed_files_data.append(img_bytes)

        except PDFConversionError:
             raise # Re-raise validation errors
        except Exception as e:
            # Catch Pillow errors (UnidentifiedImageError, etc.) or read errors
            print(f"Error processing file {file.filename}: {e}")
            raise PDFConversionError(f"Invalid or corrupted image file: {file.filename}. Error: {e}")

    if not processed_files_data:
        raise PDFConversionError("No valid JPEG images found to convert after validation.")

    try:
        output_pdf_stream = BytesIO()

        if ocr_enabled:
            # --- OCR Path ---
            merger = PdfMerger()
            try:
                for i, img in enumerate(processed_files_data): # Contains PIL Images here
                    # Create searchable PDF for each image in memory
                    # Specify language if known, e.g., lang='eng'
                    pdf_data = pytesseract.image_to_pdf_or_hocr(img, extension='pdf')
                    if not pdf_data:
                         raise PDFConversionError(f"OCR processing returned empty data for image {i+1}.")
                    pdf_stream = BytesIO(pdf_data)
                    merger.append(pdf_stream)
                    print(f"Processed image {i+1} with OCR.")
                # Write the merged PDF to the output stream
                merger.write(output_pdf_stream)
                merger.close() # Close the merger object
            except pytesseract.TesseractNotFoundError:
                 print("TesseractNotFoundError: Tesseract is not installed or not in your PATH.")
                 # Raise a specific error for the route to handle
                 raise TesseractNotFoundError("OCR Error: Tesseract is not installed or not found. Please install Tesseract and ensure it's in your system's PATH.")
            except Exception as ocr_error:
                 # Catch other potential pytesseract errors
                 print(f"Error during OCR processing: {ocr_error}")
                 raise PDFConversionError(f"An error occurred during OCR processing: {ocr_error}")
        else:
            # --- Non-OCR Path (using img2pdf) ---
            # processed_files_data contains bytes here
            pdf_bytes = img2pdf.convert(processed_files_data)
            output_pdf_stream = BytesIO(pdf_bytes)

        # Reset stream position before returning
        output_pdf_stream.seek(0)
        return output_pdf_stream

    except PDFConversionError:
        raise # Re-raise specific conversion errors
    except TesseractNotFoundError:
        raise # Re-raise Tesseract not found error
    except Exception as e:
        # Catch errors from img2pdf or PdfMerger
        print(f"Error during PDF generation: {e}")
        raise PDFConversionError(f"PDF generation failed: {e}")
