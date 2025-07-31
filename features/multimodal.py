import os
import base64
from PIL import Image
import requests
import tempfile
from io import BytesIO
import json
import google.generativeai.types as types

class MultiModalProcessor:
    def __init__(self):
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        self.supported_audio_formats = {'.mp3', '.wav', '.m4a', '.ogg'}
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.mkv'}
    
    def process_file(self, file_path):
        """Process multimodal files and return context string"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in self.supported_image_formats:
            return self._process_image(file_path)
        elif ext in self.supported_audio_formats:
            return self._process_audio(file_path)
        elif ext in self.supported_video_formats:
            return self._process_video(file_path)
        return None
    
    def _process_image(self, file_path):
        """Convert image to base64 for Gemini Vision"""
        try:
            img = Image.open(file_path)
            
            # Get image metadata
            width, height = img.size
            format_name = img.format or 'Unknown'
            
            # Resize if too large (Gemini has size limits)
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img.close()  # Explicitly close the image
            img_data = buffer.getvalue()
            
            return {
                'type': 'image',
                'data': img_data,
                'mime_type': 'image/jpeg',
                'description': f"Image file: {os.path.basename(file_path)}",
                'metadata': {
                    'original_size': f"{width}x{height}",
                    'format': format_name,
                    'file_size': os.path.getsize(file_path)
                }
            }
        except Exception as e:
            return {'type': 'error', 'message': f"Error processing image: {e}"}
    
    def _process_audio(self, file_path):
        """Transcribe audio using OpenAI Whisper API (placeholder)"""
        # Placeholder for Whisper integration
        file_size = os.path.getsize(file_path)
        return {
            'type': 'audio',
            'transcription': f"[Audio transcription placeholder for {os.path.basename(file_path)}]",
            'description': f"Audio file: {os.path.basename(file_path)}",
            'metadata': {
                'file_size': file_size,
                'duration': 'Unknown'  # Would need audio library to get duration
            }
        }
    
    def _process_video(self, file_path):
        """Extract frames from video for analysis"""
        # Placeholder for video processing
        file_size = os.path.getsize(file_path)
        return {
            'type': 'video',
            'frames': [],
            'description': f"Video file: {os.path.basename(file_path)}",
            'metadata': {
                'file_size': file_size,
                'duration': 'Unknown'  # Would need video library to get duration
            }
        }
    
    def get_image_context_for_gemini(self, file_path):
        """Get image data formatted for the Gemini Vision API."""
        image_data = self._process_image(file_path)
        if image_data and image_data.get('type') == 'image':
            # For older library versions, we might just need the raw data and mime type
            return {
                "data": image_data['data'],
                "mime_type": image_data['mime_type']
            }
        return None

    def create_multimodal_prompt(self, text_prompt, image_paths=None):
        """Create a multimodal prompt combining text and images for Gemini."""
        # This now constructs a list of dicts, compatible with older and some newer client versions
        parts = [{"type": "text", "text": text_prompt}]
        
        if image_paths:
            for image_path in image_paths:
                image_context = self.get_image_context_for_gemini(image_path)
                if image_context:
                    # The google-generativeai library expects PIL Image objects
                    try:
                        img = Image.open(BytesIO(image_context['data']))
                        parts.append(img)
                    except Exception as e:
                        print(f"Error converting image data to PIL Image: {e}")

        # The final prompt for generate_content should be just the list of parts
        # The text part is now the first element of the list.
        # We need to adjust the calling function to handle this.
        # Let's adjust the structure to be a list of the text prompt and then the images
        final_prompt_parts = [text_prompt]
        if image_paths:
            for image_path in image_paths:
                processed_image = self._process_image(image_path)
                if processed_image and processed_image.get('type') == 'image':
                    try:
                        img = Image.open(BytesIO(processed_image['data']))
                        final_prompt_parts.append(img)
                    except Exception as e:
                        print(f"Error creating PIL image: {e}")

        return final_prompt_parts