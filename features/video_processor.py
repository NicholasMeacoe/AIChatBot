"""
Enhanced Multimodal Understanding: Video Processing Component
Handles video analysis, frame extraction, and visual content understanding.
"""

import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import base64
import tempfile
from moviepy.editor import VideoFileClip
import google.generativeai as genai
from .multimodal_enhanced import AudioProcessor, VideoAnalysis, AudioAnalysis

class VideoProcessor:
    """Handles video processing and analysis"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.model_name = model_name
        self.audio_processor = AudioProcessor(model_name)
        
        # Initialize OpenCV cascades for face detection
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except:
            self.face_cascade = None
            print("Warning: Face detection cascade not available")
    
    async def analyze_video(self, file_path: str, extract_audio: bool = True, 
                           analyze_frames: bool = True, frame_interval: int = 30) -> VideoAnalysis:
        """Comprehensive video analysis"""
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")
        
        # Load video
        try:
            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened():
                raise ValueError("Failed to open video file")
        except Exception as e:
            raise ValueError(f"Failed to load video file: {e}")
        
        # Get basic video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        analysis = VideoAnalysis(
            file_path=str(file_path),
            duration=duration,
            fps=fps,
            resolution=(width, height),
            format=file_path.suffix.lower()[1:],
            frame_count=frame_count
        )
        
        # Extract and analyze audio
        if extract_audio:
            try:
                audio_analysis = await self._extract_and_analyze_audio(file_path)
                analysis.audio_analysis = audio_analysis
            except Exception as e:
                print(f"Audio analysis failed: {e}")
        
        # Analyze video frames
        if analyze_frames:
            try:
                frame_analysis = await self._analyze_video_frames(cap, frame_interval)
                analysis.scene_changes = frame_analysis["scene_changes"]
                analysis.objects_detected = frame_analysis["objects"]
                analysis.faces_detected = frame_analysis["faces"]
                analysis.text_detected = frame_analysis["text"]
                analysis.key_frames = frame_analysis["key_frames"]
                analysis.activities = frame_analysis["activities"]
            except Exception as e:
                print(f"Frame analysis failed: {e}")
        
        # AI-powered content analysis
        try:
            content_analysis = await self._ai_analyze_video_content(analysis)
            analysis.summary = content_analysis.get("summary", "")
            analysis.topics = content_analysis.get("topics", [])
        except Exception as e:
            print(f"AI content analysis failed: {e}")
        
        cap.release()
        return analysis
    
    async def _extract_and_analyze_audio(self, video_path: Path) -> Optional[AudioAnalysis]:
        """Extract audio from video and analyze it"""
        
        try:
            # Extract audio using moviepy
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                video_clip = VideoFileClip(str(video_path))
                if video_clip.audio is not None:
                    video_clip.audio.write_audiofile(temp_audio.name, verbose=False, logger=None)
                    video_clip.close()
                    
                    # Analyze the extracted audio
                    audio_analysis = await self.audio_processor.analyze_audio(temp_audio.name)
                    
                    # Clean up
                    try:
                        os.unlink(temp_audio.name)
                    except:
                        pass
                    
                    return audio_analysis
                else:
                    video_clip.close()
                    return None
                    
        except Exception as e:
            print(f"Audio extraction failed: {e}")
            return None
    
    async def _analyze_video_frames(self, cap: cv2.VideoCapture, frame_interval: int) -> Dict[str, Any]:
        """Analyze video frames for visual content"""
        
        analysis = {
            "scene_changes": [],
            "objects": [],
            "faces": [],
            "text": [],
            "key_frames": [],
            "activities": []
        }
        
        frame_number = 0
        prev_frame = None
        scene_threshold = 30.0  # Threshold for scene change detection
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_number / cap.get(cv2.CAP_PROP_FPS)
            
            # Process every nth frame
            if frame_number % frame_interval == 0:
                
                # Scene change detection
                if prev_frame is not None:
                    scene_change_score = self._calculate_frame_difference(prev_frame, frame)
                    if scene_change_score > scene_threshold:
                        analysis["scene_changes"].append(timestamp)
                
                # Face detection
                faces = self._detect_faces(frame, timestamp)
                analysis["faces"].extend(faces)
                
                # Text detection (OCR)
                text_detections = self._detect_text_in_frame(frame, timestamp)
                analysis["text"].extend(text_detections)
                
                # Object detection (basic)
                objects = self._detect_objects_basic(frame, timestamp)
                analysis["objects"].extend(objects)
                
                # Key frame detection (based on visual complexity)
                if self._is_key_frame(frame):
                    key_frame_data = {
                        "timestamp": timestamp,
                        "frame_number": frame_number,
                        "complexity_score": self._calculate_visual_complexity(frame),
                        "image_data": self._frame_to_base64(frame)
                    }
                    analysis["key_frames"].append(key_frame_data)
                
                prev_frame = frame.copy()
            
            frame_number += 1
        
        return analysis
    
    def _calculate_frame_difference(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calculate difference between two frames for scene change detection"""
        
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            
            # Calculate histogram difference
            hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
            
            # Compare histograms
            diff = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)
            return float(diff)
            
        except Exception as e:
            print(f"Error calculating frame difference: {e}")
            return 0.0
    
    def _detect_faces(self, frame: np.ndarray, timestamp: float) -> List[Dict[str, Any]]:
        """Detect faces in a frame"""
        
        faces = []
        
        if self.face_cascade is None:
            return faces
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected_faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            for (x, y, w, h) in detected_faces:
                face_data = {
                    "timestamp": timestamp,
                    "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                    "confidence": 0.8,  # Haar cascades don't provide confidence
                    "face_id": f"face_{len(faces)}"
                }
                faces.append(face_data)
                
        except Exception as e:
            print(f"Face detection error: {e}")
        
        return faces
    
    def _detect_text_in_frame(self, frame: np.ndarray, timestamp: float) -> List[Dict[str, Any]]:
        """Detect text in a frame using OCR"""
        
        text_detections = []
        
        try:
            # Use pytesseract if available
            try:
                import pytesseract
                
                # Convert frame to PIL Image
                from PIL import Image
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
                # Extract text
                text = pytesseract.image_to_string(pil_image)
                
                if text.strip():
                    text_data = {
                        "timestamp": timestamp,
                        "text": text.strip(),
                        "confidence": 0.7,  # Default confidence
                        "bbox": {"x": 0, "y": 0, "width": frame.shape[1], "height": frame.shape[0]}
                    }
                    text_detections.append(text_data)
                    
            except ImportError:
                # Fallback: simple text detection using OpenCV
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Use MSER (Maximally Stable Extremal Regions) for text detection
                mser = cv2.MSER_create()
                regions, _ = mser.detectRegions(gray)
                
                if len(regions) > 0:
                    text_data = {
                        "timestamp": timestamp,
                        "text": f"Text regions detected: {len(regions)}",
                        "confidence": 0.5,
                        "bbox": {"x": 0, "y": 0, "width": frame.shape[1], "height": frame.shape[0]}
                    }
                    text_detections.append(text_data)
                    
        except Exception as e:
            print(f"Text detection error: {e}")
        
        return text_detections
    
    def _detect_objects_basic(self, frame: np.ndarray, timestamp: float) -> List[Dict[str, Any]]:
        """Basic object detection using OpenCV methods"""
        
        objects = []
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter significant contours
            significant_contours = [c for c in contours if cv2.contourArea(c) > 1000]
            
            for i, contour in enumerate(significant_contours[:10]):  # Limit to 10 objects
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                object_data = {
                    "timestamp": timestamp,
                    "object_id": f"object_{i}",
                    "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                    "area": float(area),
                    "confidence": 0.6,
                    "type": "unknown_object"
                }
                objects.append(object_data)
                
        except Exception as e:
            print(f"Object detection error: {e}")
        
        return objects
    
    def _is_key_frame(self, frame: np.ndarray) -> bool:
        """Determine if a frame is a key frame based on visual complexity"""
        
        try:
            complexity = self._calculate_visual_complexity(frame)
            # Consider frames with high visual complexity as key frames
            return complexity > 50.0
        except:
            return False
    
    def _calculate_visual_complexity(self, frame: np.ndarray) -> float:
        """Calculate visual complexity of a frame"""
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Return mean gradient magnitude as complexity measure
            return float(np.mean(magnitude))
            
        except Exception as e:
            print(f"Error calculating visual complexity: {e}")
            return 0.0
    
    def _frame_to_base64(self, frame: np.ndarray, max_size: Tuple[int, int] = (320, 240)) -> str:
        """Convert frame to base64 encoded image"""
        
        try:
            # Resize frame if too large
            height, width = frame.shape[:2]
            if width > max_size[0] or height > max_size[1]:
                scale = min(max_size[0]/width, max_size[1]/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # Encode as JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Convert to base64
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            return image_base64
            
        except Exception as e:
            print(f"Error converting frame to base64: {e}")
            return ""
    
    async def _ai_analyze_video_content(self, analysis: VideoAnalysis) -> Dict[str, Any]:
        """Use AI to analyze video content and generate insights"""
        
        # Prepare context for AI analysis
        context = {
            "duration": analysis.duration,
            "resolution": analysis.resolution,
            "fps": analysis.fps,
            "scene_changes": len(analysis.scene_changes),
            "faces_detected": len(analysis.faces_detected),
            "text_detected": len(analysis.text_detected),
            "objects_detected": len(analysis.objects_detected),
            "key_frames": len(analysis.key_frames)
        }
        
        # Include audio analysis if available
        if analysis.audio_analysis:
            context["audio"] = {
                "transcription": analysis.audio_analysis.transcription,
                "language": analysis.audio_analysis.language,
                "topics": analysis.audio_analysis.topics,
                "summary": analysis.audio_analysis.summary
            }
        
        # Include sample text detections
        if analysis.text_detected:
            context["sample_text"] = [t["text"] for t in analysis.text_detected[:5]]
        
        analysis_prompt = f"""
        Analyze the following video content and provide insights:
        
        Video Context: {json.dumps(context, indent=2)}
        
        Please provide a JSON response with the following analysis:
        {{
            "summary": "Brief summary of the video content",
            "topics": ["topic1", "topic2", "topic3"],
            "content_type": "educational|entertainment|presentation|meeting|other",
            "key_moments": [
                {{"timestamp": 30.5, "description": "Important moment description"}},
                {{"timestamp": 120.0, "description": "Another key moment"}}
            ],
            "visual_elements": ["charts", "text", "people", "objects"],
            "overall_sentiment": "positive|negative|neutral",
            "recommended_actions": ["action1", "action2"],
            "accessibility_notes": "Notes about accessibility features or needs"
        }}
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(analysis_prompt)
            
            content_analysis = json.loads(response.text.strip())
            return content_analysis
            
        except Exception as e:
            print(f"AI video analysis failed: {e}")
            return {
                "summary": "Analysis failed",
                "topics": [],
                "content_type": "unknown",
                "key_moments": [],
                "visual_elements": [],
                "overall_sentiment": "neutral",
                "recommended_actions": [],
                "accessibility_notes": ""
            }
    
    def extract_frames_at_timestamps(self, video_path: str, timestamps: List[float]) -> List[Dict[str, Any]]:
        """Extract specific frames at given timestamps"""
        
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            for timestamp in timestamps:
                frame_number = int(timestamp * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                ret, frame = cap.read()
                if ret:
                    frame_data = {
                        "timestamp": timestamp,
                        "frame_number": frame_number,
                        "image_data": self._frame_to_base64(frame),
                        "resolution": (frame.shape[1], frame.shape[0])
                    }
                    frames.append(frame_data)
            
            cap.release()
            
        except Exception as e:
            print(f"Error extracting frames: {e}")
        
        return frames
    
    def create_video_summary_gif(self, video_path: str, output_path: str, 
                                max_frames: int = 10, duration_per_frame: float = 0.5) -> bool:
        """Create a GIF summary of the video using key frames"""
        
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Select evenly spaced frames
            frame_indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
            
            frames = []
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Resize for GIF
                    frame_resized = cv2.resize(frame_rgb, (320, 240))
                    frames.append(frame_resized)
            
            cap.release()
            
            # Create GIF using PIL
            if frames:
                from PIL import Image
                pil_frames = [Image.fromarray(frame) for frame in frames]
                pil_frames[0].save(
                    output_path,
                    save_all=True,
                    append_images=pil_frames[1:],
                    duration=int(duration_per_frame * 1000),
                    loop=0
                )
                return True
            
        except Exception as e:
            print(f"Error creating video summary GIF: {e}")
        
        return False

# Global video processor instance
video_processor = VideoProcessor()
