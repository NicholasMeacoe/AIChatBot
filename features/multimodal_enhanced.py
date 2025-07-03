"""
Enhanced Multimodal Understanding: Audio & Video Analysis Feature
Provides comprehensive audio and video processing capabilities with AI analysis.
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import base64
import tempfile
import subprocess

# Audio processing imports
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
import numpy as np

# Video processing imports
import cv2
from moviepy.editor import VideoFileClip
import matplotlib.pyplot as plt

# AI and ML imports
import google.generativeai as genai
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

@dataclass
class AudioAnalysis:
    file_path: str
    duration: float
    sample_rate: int
    channels: int
    format: str
    transcription: str = ""
    language: str = "unknown"
    confidence: float = 0.0
    speaker_segments: List[Dict[str, Any]] = field(default_factory=list)
    emotions: List[Dict[str, Any]] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    summary: str = ""
    topics: List[str] = field(default_factory=list)
    sentiment: Dict[str, float] = field(default_factory=dict)
    noise_level: float = 0.0
    speech_rate: float = 0.0  # words per minute
    
@dataclass
class VideoAnalysis:
    file_path: str
    duration: float
    fps: float
    resolution: Tuple[int, int]
    format: str
    frame_count: int
    audio_analysis: Optional[AudioAnalysis] = None
    scene_changes: List[float] = field(default_factory=list)  # timestamps
    objects_detected: List[Dict[str, Any]] = field(default_factory=list)
    faces_detected: List[Dict[str, Any]] = field(default_factory=list)
    text_detected: List[Dict[str, Any]] = field(default_factory=list)
    key_frames: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    topics: List[str] = field(default_factory=list)
    activities: List[Dict[str, Any]] = field(default_factory=list)

class AudioProcessor:
    """Handles audio processing and analysis"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.model_name = model_name
        self.recognizer = sr.Recognizer()
        self.whisper_model = None
        
        if WHISPER_AVAILABLE:
            try:
                self.whisper_model = whisper.load_model("base")
            except Exception as e:
                print(f"Failed to load Whisper model: {e}")
    
    async def analyze_audio(self, file_path: str) -> AudioAnalysis:
        """Comprehensive audio analysis"""
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        # Load audio file
        try:
            audio = AudioSegment.from_file(str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to load audio file: {e}")
        
        # Basic audio properties
        analysis = AudioAnalysis(
            file_path=str(file_path),
            duration=len(audio) / 1000.0,  # Convert to seconds
            sample_rate=audio.frame_rate,
            channels=audio.channels,
            format=file_path.suffix.lower()[1:]
        )
        
        # Transcribe audio
        analysis.transcription, analysis.language, analysis.confidence = await self._transcribe_audio(audio)
        
        # Analyze speech characteristics
        analysis.speech_rate = self._calculate_speech_rate(analysis.transcription, analysis.duration)
        analysis.noise_level = self._calculate_noise_level(audio)
        
        # Detect speaker segments
        analysis.speaker_segments = self._detect_speaker_segments(audio)
        
        # AI-powered analysis
        if analysis.transcription:
            ai_analysis = await self._ai_analyze_audio_content(analysis.transcription)
            analysis.emotions = ai_analysis.get("emotions", [])
            analysis.key_phrases = ai_analysis.get("key_phrases", [])
            analysis.summary = ai_analysis.get("summary", "")
            analysis.topics = ai_analysis.get("topics", [])
            analysis.sentiment = ai_analysis.get("sentiment", {})
        
        return analysis
    
    async def _transcribe_audio(self, audio: AudioSegment) -> Tuple[str, str, float]:
        """Transcribe audio to text using multiple methods"""
        
        transcription = ""
        language = "unknown"
        confidence = 0.0
        
        # Convert to WAV for processing
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio.export(temp_file.name, format="wav")
            temp_path = temp_file.name
        
        try:
            # Try Whisper first (if available)
            if self.whisper_model:
                try:
                    result = self.whisper_model.transcribe(temp_path)
                    transcription = result["text"]
                    language = result.get("language", "unknown")
                    confidence = 0.9  # Whisper is generally reliable
                except Exception as e:
                    print(f"Whisper transcription failed: {e}")
            
            # Fallback to speech_recognition
            if not transcription:
                with sr.AudioFile(temp_path) as source:
                    audio_data = self.recognizer.record(source)
                    try:
                        transcription = self.recognizer.recognize_google(audio_data)
                        language = "en"  # Google Speech Recognition default
                        confidence = 0.7
                    except sr.UnknownValueError:
                        transcription = ""
                    except sr.RequestError as e:
                        print(f"Speech recognition error: {e}")
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
        
        return transcription, language, confidence
    
    def _calculate_speech_rate(self, transcription: str, duration: float) -> float:
        """Calculate words per minute"""
        if not transcription or duration <= 0:
            return 0.0
        
        word_count = len(transcription.split())
        return (word_count / duration) * 60
    
    def _calculate_noise_level(self, audio: AudioSegment) -> float:
        """Calculate relative noise level"""
        try:
            # Convert to numpy array
            samples = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
                samples = samples.mean(axis=1)
            
            # Calculate RMS (Root Mean Square) as noise indicator
            rms = np.sqrt(np.mean(samples**2))
            
            # Normalize to 0-1 scale
            max_possible = 2**(audio.sample_width * 8 - 1)
            return min(rms / max_possible, 1.0)
            
        except Exception as e:
            print(f"Error calculating noise level: {e}")
            return 0.0
    
    def _detect_speaker_segments(self, audio: AudioSegment) -> List[Dict[str, Any]]:
        """Detect different speaker segments (basic implementation)"""
        
        segments = []
        
        try:
            # Split on silence to find speech segments
            chunks = split_on_silence(
                audio,
                min_silence_len=1000,  # 1 second
                silence_thresh=audio.dBFS - 14,
                keep_silence=500
            )
            
            current_time = 0
            for i, chunk in enumerate(chunks):
                segment = {
                    "segment_id": i,
                    "start_time": current_time,
                    "end_time": current_time + len(chunk) / 1000.0,
                    "duration": len(chunk) / 1000.0,
                    "speaker_id": f"speaker_{i % 2}",  # Simple alternating assumption
                    "volume": chunk.dBFS
                }
                segments.append(segment)
                current_time = segment["end_time"]
        
        except Exception as e:
            print(f"Error detecting speaker segments: {e}")
        
        return segments
    
    async def _ai_analyze_audio_content(self, transcription: str) -> Dict[str, Any]:
        """Use AI to analyze transcribed audio content"""
        
        analysis_prompt = f"""
        Analyze the following transcribed audio content and provide insights:
        
        Transcription: {transcription}
        
        Please provide a JSON response with the following analysis:
        {{
            "summary": "Brief summary of the content",
            "topics": ["topic1", "topic2", "topic3"],
            "key_phrases": ["phrase1", "phrase2", "phrase3"],
            "emotions": [
                {{"emotion": "happy", "confidence": 0.8, "timestamp_range": [0, 30]}},
                {{"emotion": "concerned", "confidence": 0.6, "timestamp_range": [30, 60]}}
            ],
            "sentiment": {{"positive": 0.6, "negative": 0.2, "neutral": 0.2}},
            "intent": "informational|question|request|complaint|other",
            "urgency": "low|medium|high",
            "action_items": ["action1", "action2"]
        }}
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(analysis_prompt)
            
            analysis = json.loads(response.text.strip())
            return analysis
            
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return {
                "summary": "Analysis failed",
                "topics": [],
                "key_phrases": [],
                "emotions": [],
                "sentiment": {"neutral": 1.0},
                "intent": "unknown",
                "urgency": "low",
                "action_items": []
            }
    
    def extract_audio_features(self, file_path: str) -> Dict[str, Any]:
        """Extract detailed audio features for analysis"""
        
        try:
            audio = AudioSegment.from_file(file_path)
            samples = np.array(audio.get_array_of_samples())
            
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
                samples = samples.mean(axis=1)
            
            features = {
                "duration": len(audio) / 1000.0,
                "sample_rate": audio.frame_rate,
                "channels": audio.channels,
                "bit_depth": audio.sample_width * 8,
                "file_size": os.path.getsize(file_path),
                "average_volume": audio.dBFS,
                "max_volume": audio.max_dBFS,
                "rms_energy": np.sqrt(np.mean(samples**2)),
                "zero_crossing_rate": self._calculate_zero_crossing_rate(samples),
                "spectral_centroid": self._calculate_spectral_centroid(samples, audio.frame_rate)
            }
            
            return features
            
        except Exception as e:
            print(f"Error extracting audio features: {e}")
            return {}
    
    def _calculate_zero_crossing_rate(self, samples: np.ndarray) -> float:
        """Calculate zero crossing rate"""
        try:
            zero_crossings = np.where(np.diff(np.sign(samples)))[0]
            return len(zero_crossings) / len(samples)
        except:
            return 0.0
    
    def _calculate_spectral_centroid(self, samples: np.ndarray, sample_rate: int) -> float:
        """Calculate spectral centroid (brightness measure)"""
        try:
            # Simple FFT-based spectral centroid
            fft = np.fft.fft(samples)
            magnitude = np.abs(fft)
            freqs = np.fft.fftfreq(len(fft), 1/sample_rate)
            
            # Only use positive frequencies
            positive_freqs = freqs[:len(freqs)//2]
            positive_magnitude = magnitude[:len(magnitude)//2]
            
            if np.sum(positive_magnitude) > 0:
                centroid = np.sum(positive_freqs * positive_magnitude) / np.sum(positive_magnitude)
                return float(centroid)
            else:
                return 0.0
                
        except Exception as e:
            print(f"Error calculating spectral centroid: {e}")
            return 0.0
