from flask import Blueprint, request, jsonify, send_file
from io import BytesIO

# Import PDF utility functions and custom exceptions
from pdf_utils import convert_images_to_pdf, PDFConversionError, TesseractNotFoundError

# Create Blueprint
pdf_bp = Blueprint('pdf', __name__)

@pdf_bp.route('/convert', methods=['POST'])
def convert_images_to_pdf_endpoint():
    """API endpoint to handle multiple image uploads and convert them to a single PDF."""
    if 'images' not in request.files:
        return jsonify({"error": "No 'images' part in the request"}), 400

    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        # Handle case where 'images' part exists but no files were selected
        return jsonify({"error": "No image files selected"}), 400

    # Check if OCR is requested (convert string 'true'/'false' to boolean)
    ocr_enabled = request.form.get('ocr_enabled', 'false').lower() == 'true'

    try:
        # Call the utility function to perform the conversion
        pdf_stream = convert_images_to_pdf(files, ocr_enabled=ocr_enabled)

        # Send the generated PDF file back to the client
        return send_file(
            pdf_stream,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='converted_images.pdf'
        )

    except TesseractNotFoundError as e:
        # Handle Tesseract not found specifically (HTTP 500 - Server Error)
        print(f"Tesseract Error: {e}")
        return jsonify({"error": str(e)}), 500
    except PDFConversionError as e:
        # Handle validation or conversion errors (HTTP 400 - Bad Request)
        print(f"PDF Conversion Error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # Catch any other unexpected errors during the process (HTTP 500)
        print(f"Unexpected error during PDF conversion: {e}")
        return jsonify({"error": f"An unexpected server error occurred during PDF conversion."}), 500
