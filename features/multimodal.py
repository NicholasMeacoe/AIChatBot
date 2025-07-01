import os
import base64
from PIL import Image
import requests
import tempfile
from io import BytesIO

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
            # Resize if too large
            if img.width > 1024 or img.height > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format='JPEG')
            img.close()  # Explicitly close the image
            img_data = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                'type': 'image',
                'data': img_data,
                'mime_type': 'image/jpeg',
                'description': f"Image file: {os.path.basename(file_path)}"
            }
        except Exception as e:
            return {'type': 'error', 'message': f"Error processing image: {e}"}
    
    def _process_audio(self, file_path):
        """Transcribe audio using OpenAI Whisper API (placeholder)"""
        # Placeholder for Whisper integration
        return {
            'type': 'audio',
            'transcription': f"[Audio transcription placeholder for {os.path.basename(file_path)}]",
            'description': f"Audio file: {os.path.basename(file_path)}"
        }
    
    def _process_video(self, file_path):
        """Extract frames from video for analysis"""
        # Placeholder for video processing
        return {
            'type': 'video',
            'frames': [],
            'description': f"Video file: {os.path.basename(file_path)}"
        }