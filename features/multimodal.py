import os
import base64
from PIL import Image
import requests
import tempfile
from io import BytesIO
import json
import google.generativeai.types as types
import cv2
import speech_recognition as sr
from pydub import AudioSegment
from mutagen import File as MutagenFile
import numpy as np
import logging

class MultiModalProcessor:
    def __init__(self):
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
        self.supported_audio_formats = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.wma'}
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        self.speech_recognizer = sr.Recognizer()
        self.logger = logging.getLogger(__name__)
    
    def process_file(self, file_path):
        """Process multimodal files and return context string"""
        if not os.path.exists(file_path):
            return {'type': 'error', 'message': f"File not found: {file_path}"}
        
        file_type = self.detect_file_type(file_path)
        
        try:
            if file_type == 'image':
                return self._process_image(file_path)
            elif file_type == 'audio':
                return self._process_audio(file_path)
            elif file_type == 'video':
                return self._process_video(file_path)
            else:
                return {'type': 'unsupported', 'message': f"Unsupported file type: {file_type}"}
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return {'type': 'error', 'message': f"Error processing file: {str(e)}"}
    
    def detect_file_type(self, file_path):
        """Enhanced file type detection using extension and content analysis"""
        ext = os.path.splitext(file_path)[1].lower()
        
        # Primary detection by extension
        if ext in self.supported_image_formats:
            return 'image'
        elif ext in self.supported_audio_formats:
            return 'audio'
        elif ext in self.supported_video_formats:
            return 'video'
        
        # Secondary detection by content (magic bytes)
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
                
            # Image magic bytes
            if header.startswith(b'\xff\xd8\xff'):  # JPEG
                return 'image'
            elif header.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                return 'image'
            elif header.startswith(b'GIF8'):  # GIF
                return 'image'
            elif header.startswith(b'RIFF') and b'WEBP' in header:  # WebP
                return 'image'
            
            # Audio magic bytes
            elif header.startswith(b'ID3') or header[1:4] == b'ID3':  # MP3
                return 'audio'
            elif header.startswith(b'RIFF') and b'WAVE' in header:  # WAV
                return 'audio'
            elif header.startswith(b'OggS'):  # OGG
                return 'audio'
            elif header.startswith(b'fLaC'):  # FLAC
                return 'audio'
            
            # Video magic bytes
            elif header[4:8] == b'ftyp':  # MP4/M4V
                return 'video'
            elif header.startswith(b'RIFF') and b'AVI ' in header:  # AVI
                return 'video'
            elif header.startswith(b'\x1a\x45\xdf\xa3'):  # MKV
                return 'video'
                
        except Exception as e:
            self.logger.warning(f"Could not read file header for {file_path}: {e}")
        
        return 'unknown'
    
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
        """Transcribe audio using speech recognition"""
        try:
            # Extract comprehensive metadata
            metadata = self._extract_audio_metadata(file_path)
            
            # Convert audio to WAV format for speech recognition
            transcription = self._transcribe_audio(file_path)
            
            return {
                'type': 'audio',
                'transcription': transcription,
                'description': f"Audio file: {os.path.basename(file_path)}",
                'metadata': metadata
            }
        except Exception as e:
            self.logger.error(f"Error processing audio {file_path}: {e}")
            return {
                'type': 'error',
                'message': f"Error processing audio: {str(e)}",
                'metadata': {'file_size': os.path.getsize(file_path)}
            }
    
    def _extract_audio_metadata(self, file_path):
        """Extract comprehensive audio metadata"""
        metadata = {
            'file_size': os.path.getsize(file_path),
            'format': os.path.splitext(file_path)[1][1:].upper()
        }
        
        try:
            # Use mutagen for detailed metadata
            audio_file = MutagenFile(file_path)
            if audio_file is not None:
                if hasattr(audio_file, 'info'):
                    info = audio_file.info
                    metadata.update({
                        'duration': round(info.length, 2) if hasattr(info, 'length') else 'Unknown',
                        'bitrate': getattr(info, 'bitrate', 'Unknown'),
                        'sample_rate': getattr(info, 'sample_rate', 'Unknown'),
                        'channels': getattr(info, 'channels', 'Unknown')
                    })
                
                # Extract tags
                tags = {}
                if audio_file.tags:
                    for key, value in audio_file.tags.items():
                        if isinstance(value, list) and len(value) > 0:
                            tags[key] = str(value[0])
                        else:
                            tags[key] = str(value)
                
                if tags:
                    metadata['tags'] = tags
            
            # Fallback using pydub for basic info
            if metadata.get('duration') == 'Unknown':
                try:
                    audio = AudioSegment.from_file(file_path)
                    metadata.update({
                        'duration': round(len(audio) / 1000.0, 2),  # Convert ms to seconds
                        'channels': audio.channels,
                        'sample_rate': audio.frame_rate,
                        'sample_width': audio.sample_width
                    })
                except Exception as e:
                    self.logger.warning(f"Could not extract audio info with pydub: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Could not extract audio metadata: {e}")
        
        return metadata
    
    def _transcribe_audio(self, file_path):
        """Transcribe audio to text using speech recognition"""
        try:
            # Convert to WAV format if needed
            audio = AudioSegment.from_file(file_path)
            
            # Convert to mono and appropriate sample rate for better recognition
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                audio.export(temp_wav.name, format='wav')
                temp_wav_path = temp_wav.name
            
            try:
                # Use speech recognition
                with sr.AudioFile(temp_wav_path) as source:
                    # Adjust for ambient noise
                    self.speech_recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = self.speech_recognizer.record(source)
                
                # Try multiple recognition engines
                transcription = None
                
                # Try Google Speech Recognition (free tier)
                try:
                    transcription = self.speech_recognizer.recognize_google(audio_data)
                    self.logger.info("Successfully transcribed using Google Speech Recognition")
                except sr.UnknownValueError:
                    transcription = "[Speech could not be understood]"
                except sr.RequestError as e:
                    self.logger.warning(f"Google Speech Recognition error: {e}")
                    
                    # Fallback to offline recognition if available
                    try:
                        transcription = self.speech_recognizer.recognize_sphinx(audio_data)
                        self.logger.info("Successfully transcribed using offline Sphinx")
                    except (sr.UnknownValueError, sr.RequestError):
                        transcription = "[Audio transcription unavailable - speech recognition service error]"
                
                return transcription or "[No speech detected in audio]"
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_wav_path)
                except Exception:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Audio transcription failed: {e}")
            return f"[Audio transcription failed: {str(e)}]"
    
    def _process_video(self, file_path):
        """Extract frames from video for analysis using OpenCV"""
        try:
            # Extract comprehensive metadata
            metadata = self._extract_video_metadata(file_path)
            
            # Extract key frames for analysis
            frames = self._extract_video_frames(file_path, max_frames=5)
            
            return {
                'type': 'video',
                'frames': frames,
                'description': f"Video file: {os.path.basename(file_path)}",
                'metadata': metadata
            }
        except Exception as e:
            self.logger.error(f"Error processing video {file_path}: {e}")
            return {
                'type': 'error',
                'message': f"Error processing video: {str(e)}",
                'metadata': {'file_size': os.path.getsize(file_path)}
            }
    
    def _extract_video_metadata(self, file_path):
        """Extract comprehensive video metadata using OpenCV"""
        metadata = {
            'file_size': os.path.getsize(file_path),
            'format': os.path.splitext(file_path)[1][1:].upper()
        }
        
        try:
            cap = cv2.VideoCapture(file_path)
            
            if cap.isOpened():
                # Basic video properties
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                duration = frame_count / fps if fps > 0 else 0
                
                metadata.update({
                    'duration': round(duration, 2),
                    'fps': round(fps, 2),
                    'frame_count': frame_count,
                    'resolution': f"{width}x{height}",
                    'width': width,
                    'height': height,
                    'aspect_ratio': round(width / height, 2) if height > 0 else 'Unknown'
                })
                
                # Additional codec information
                fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
                codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
                metadata['codec'] = codec.strip()
                
            cap.release()
            
        except Exception as e:
            self.logger.warning(f"Could not extract video metadata: {e}")
        
        return metadata
    
    def _extract_video_frames(self, file_path, max_frames=5):
        """Extract key frames from video for analysis"""
        frames = []
        
        try:
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                return frames
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if frame_count == 0:
                cap.release()
                return frames
            
            # Calculate frame indices to extract (evenly distributed)
            if frame_count <= max_frames:
                frame_indices = list(range(0, frame_count, max(1, frame_count // max_frames)))
            else:
                frame_indices = [int(i * frame_count / max_frames) for i in range(max_frames)]
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # Convert frame to PIL Image for consistency with image processing
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # Resize frame if too large
                    max_size = 1024
                    if pil_image.width > max_size or pil_image.height > max_size:
                        pil_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    
                    # Convert to bytes for storage
                    buffer = BytesIO()
                    pil_image.save(buffer, format='JPEG', quality=85)
                    frame_data = buffer.getvalue()
                    
                    frames.append({
                        'frame_index': frame_idx,
                        'timestamp': round(frame_idx / cap.get(cv2.CAP_PROP_FPS), 2) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0,
                        'data': frame_data,
                        'mime_type': 'image/jpeg',
                        'size': f"{pil_image.width}x{pil_image.height}"
                    })
            
            cap.release()
            
        except Exception as e:
            self.logger.error(f"Error extracting video frames: {e}")
        
        return frames
    
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

    def get_video_frames_for_gemini(self, file_path):
        """Get video frames formatted for Gemini Vision API"""
        video_data = self._process_video(file_path)
        if video_data and video_data.get('type') == 'video':
            frames = []
            for frame_info in video_data.get('frames', []):
                try:
                    img = Image.open(BytesIO(frame_info['data']))
                    frames.append({
                        'image': img,
                        'timestamp': frame_info['timestamp'],
                        'frame_index': frame_info['frame_index']
                    })
                except Exception as e:
                    self.logger.error(f"Error converting video frame to PIL Image: {e}")
            return frames
        return []
    
    def get_audio_context_for_gemini(self, file_path):
        """Get audio transcription for text-based Gemini processing"""
        audio_data = self._process_audio(file_path)
        if audio_data and audio_data.get('type') == 'audio':
            return {
                'transcription': audio_data.get('transcription', ''),
                'metadata': audio_data.get('metadata', {}),
                'description': audio_data.get('description', '')
            }
        return None
    
    def create_multimodal_prompt(self, text_prompt, file_paths=None):
        """Create a multimodal prompt combining text, images, and processed multimedia for Gemini."""
        final_prompt_parts = [text_prompt]
        
        if file_paths:
            for file_path in file_paths:
                file_type = self.detect_file_type(file_path)
                
                if file_type == 'image':
                    processed_image = self._process_image(file_path)
                    if processed_image and processed_image.get('type') == 'image':
                        try:
                            img = Image.open(BytesIO(processed_image['data']))
                            final_prompt_parts.append(img)
                        except Exception as e:
                            self.logger.error(f"Error creating PIL image: {e}")
                
                elif file_type == 'video':
                    # For video, add key frames and description to prompt
                    video_frames = self.get_video_frames_for_gemini(file_path)
                    if video_frames:
                        # Add a text description of the video
                        video_data = self._process_video(file_path)
                        metadata = video_data.get('metadata', {})
                        video_description = f"\n[VIDEO ANALYSIS: {os.path.basename(file_path)}]\n"
                        video_description += f"Duration: {metadata.get('duration', 'Unknown')}s, "
                        video_description += f"Resolution: {metadata.get('resolution', 'Unknown')}, "
                        video_description += f"FPS: {metadata.get('fps', 'Unknown')}\n"
                        video_description += f"Extracted {len(video_frames)} key frames for analysis:\n"
                        
                        final_prompt_parts.append(video_description)
                        
                        # Add the key frames
                        for i, frame_info in enumerate(video_frames):
                            final_prompt_parts.append(f"Frame {i+1} (at {frame_info['timestamp']}s):")
                            final_prompt_parts.append(frame_info['image'])
                
                elif file_type == 'audio':
                    # For audio, add transcription to prompt
                    audio_context = self.get_audio_context_for_gemini(file_path)
                    if audio_context:
                        audio_description = f"\n[AUDIO ANALYSIS: {audio_context['description']}]\n"
                        metadata = audio_context.get('metadata', {})
                        if metadata.get('duration') != 'Unknown':
                            audio_description += f"Duration: {metadata.get('duration')}s, "
                        if metadata.get('format'):
                            audio_description += f"Format: {metadata.get('format')}\n"
                        
                        transcription = audio_context.get('transcription', '')
                        if transcription and not transcription.startswith('['):
                            audio_description += f"Transcription: {transcription}\n"
                        else:
                            audio_description += f"Transcription status: {transcription}\n"
                        
                        final_prompt_parts.append(audio_description)

        return final_prompt_parts
    
    def get_supported_formats(self):
        """Return all supported multimedia formats"""
        return {
            'image': list(self.supported_image_formats),
            'audio': list(self.supported_audio_formats),
            'video': list(self.supported_video_formats)
        }
    
    def is_multimedia_file(self, file_path):
        """Check if file is a supported multimedia file"""
        file_type = self.detect_file_type(file_path)
        return file_type in ['image', 'audio', 'video']