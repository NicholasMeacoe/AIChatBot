import tempfile
import os
from io import BytesIO
import wave

try:
    import speech_recognition as sr
    import pyttsx3
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

class VoiceInterface:
    def __init__(self):
        if not VOICE_AVAILABLE:
            self.available = False
            return
        
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.tts_engine = pyttsx3.init()
            self.setup_tts()
            self.available = True
        except Exception:
            self.available = False
    
    def setup_tts(self):
        """Configure text-to-speech settings"""
        voices = self.tts_engine.getProperty('voices')
        if voices:
            self.tts_engine.setProperty('voice', voices[0].id)
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.8)
    
    def speech_to_text(self, audio_data=None, audio_file=None):
        """Convert speech to text"""
        if not self.available:
            return {'success': False, 'error': 'Voice interface not available'}
        
        try:
            if audio_file:
                with sr.AudioFile(audio_file) as source:
                    audio = self.recognizer.record(source)
            elif audio_data:
                audio = sr.AudioData(audio_data, 16000, 2)
            else:
                # Record from microphone
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                    print("Listening...")
                    audio = self.recognizer.listen(source, timeout=10)
            
            text = self.recognizer.recognize_google(audio)
            return {'success': True, 'text': text}
            
        except sr.UnknownValueError:
            return {'success': False, 'error': 'Could not understand audio'}
        except sr.RequestError as e:
            return {'success': False, 'error': f'Speech recognition error: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Error: {e}'}
    
    def text_to_speech(self, text, output_file=None):
        """Convert text to speech"""
        if not self.available:
            return {'success': False, 'error': 'Voice interface not available'}
        
        try:
            if output_file:
                self.tts_engine.save_to_file(text, output_file)
                self.tts_engine.runAndWait()
                return {'success': True, 'file': output_file}
            else:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                return {'success': True}
                
        except Exception as e:
            return {'success': False, 'error': f'TTS error: {e}'}
    
    def process_voice_command(self, text):
        """Process voice commands"""
        text_lower = text.lower()
        
        commands = {
            'clear context': 'clear_context',
            'send message': 'send_message',
            'new conversation': 'new_conversation',
            'export chat': 'export_chat',
            'summarize': 'summarize_context'
        }
        
        for phrase, command in commands.items():
            if phrase in text_lower:
                return {'command': command, 'text': text}
        
        return {'command': 'message', 'text': text}
    
    def create_audio_response(self, text):
        """Create audio file from text response"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            result = self.text_to_speech(text, temp_file.name)
            if result['success']:
                return temp_file.name
        return None