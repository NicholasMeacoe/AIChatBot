import os
import re
import json
from datetime import datetime, timedelta
import google.generativeai as genai

class SmartContextManager:
    def __init__(self, api_key, allowed_context_dir):
        self.api_key = api_key
        self.allowed_context_dir = allowed_context_dir
        self.context_history = []
        self.relevance_threshold = 0.7
    
    def analyze_conversation_for_context(self, conversation_text):
        """Analyze conversation to suggest relevant context"""
        suggestions = []
        
        # Extract file mentions
        file_patterns = [
            r'(?:file|document|script|code)\s+(?:called|named|titled)\s+([^\s]+)',
            r'([^\s]+\.(?:py|js|html|css|json|txt|md|csv))',
            r'(?:in|from|see)\s+([^\s]+/[^\s]+)'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, conversation_text, re.IGNORECASE)
            for match in matches:
                file_path = self._find_file_in_context_dir(match)
                if file_path:
                    suggestions.append({
                        'type': 'file',
                        'path': file_path,
                        'relevance': 0.8,
                        'reason': f'File mentioned in conversation: {match}'
                    })
        
        # Extract URL mentions
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, conversation_text)
        for url in urls:
            suggestions.append({
                'type': 'url',
                'path': url,
                'relevance': 0.9,
                'reason': 'URL mentioned in conversation'
            })
        
        # Topic-based suggestions
        topics = self._extract_topics(conversation_text)
        for topic in topics:
            related_files = self._find_files_by_topic(topic)
            for file_path in related_files:
                suggestions.append({
                    'type': 'file',
                    'path': file_path,
                    'relevance': 0.6,
                    'reason': f'Related to topic: {topic}'
                })
        
        return sorted(suggestions, key=lambda x: x['relevance'], reverse=True)
    
    def _find_file_in_context_dir(self, filename):
        """Find file in allowed context directory"""
        for root, dirs, files in os.walk(self.allowed_context_dir):
            for file in files:
                if filename.lower() in file.lower():
                    return os.path.relpath(os.path.join(root, file), self.allowed_context_dir)
        return None
    
    def _extract_topics(self, text):
        """Extract main topics from text"""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        common_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 'which', 'their', 'time', 'about', 'code', 'file', 'help', 'need', 'want', 'like', 'know', 'think'}
        
        word_freq = {}
        for word in words:
            if word not in common_words and len(word) > 4:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        return [word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]]
    
    def _find_files_by_topic(self, topic):
        """Find files related to a topic"""
        related_files = []
        for root, dirs, files in os.walk(self.allowed_context_dir):
            for file in files:
                if topic.lower() in file.lower():
                    file_path = os.path.relpath(os.path.join(root, file), self.allowed_context_dir)
                    related_files.append(file_path)
        return related_files
    
    def score_context_relevance(self, context_items, conversation):
        """Score relevance of current context items"""
        if not self.api_key:
            return {}
        
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            prompt = f"""
            Rate the relevance of these context items to the conversation (0-1 scale):
            
            Conversation: {conversation[-500:]}  # Last 500 chars
            
            Context items: {json.dumps(context_items)}
            
            Return JSON with item:score pairs.
            """
            
            response = model.generate_content(prompt)
            return json.loads(response.text)
        except:
            return {}
    
    def cleanup_irrelevant_context(self, context_items, conversation, threshold=0.3):
        """Remove context items with low relevance scores"""
        scores = self.score_context_relevance(context_items, conversation)
        return [item for item in context_items if scores.get(item, 1.0) > threshold]