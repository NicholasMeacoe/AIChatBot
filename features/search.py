import sqlite3
import json
import re
from datetime import datetime

class SearchManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.init_search_tables()
    
    def init_search_tables(self):
        """Initialize search-related tables"""
        cursor = self.db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                tag TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES history (id)
            )
        """)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS message_search USING fts5(
                message_id, user_message, bot_response, context_info
            )
        """)
        self.db.commit()
    
    def index_message(self, message_id, user_message, bot_response, context_info):
        """Add message to search index"""
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO message_search 
            (message_id, user_message, bot_response, context_info)
            VALUES (?, ?, ?, ?)
        """, (message_id, user_message, bot_response, context_info or ''))
        self.db.commit()
    
    def search_messages(self, query, limit=50):
        """Full-text search across messages"""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT h.*, rank FROM message_search 
            JOIN history h ON h.id = message_search.message_id
            WHERE message_search MATCH ? 
            ORDER BY rank LIMIT ?
        """, (query, limit))
        return cursor.fetchall()
    
    def add_tag(self, conversation_id, tag):
        """Add tag to conversation"""
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO conversation_tags (conversation_id, tag)
            VALUES (?, ?)
        """, (conversation_id, tag.lower().strip()))
        self.db.commit()
    
    def get_tags(self, conversation_id=None):
        """Get tags for conversation or all tags"""
        cursor = self.db.cursor()
        if conversation_id:
            cursor.execute("""
                SELECT tag FROM conversation_tags 
                WHERE conversation_id = ?
            """, (conversation_id,))
        else:
            cursor.execute("""
                SELECT tag, COUNT(*) as count FROM conversation_tags 
                GROUP BY tag ORDER BY count DESC
            """)
        return cursor.fetchall()
    
    def search_by_tags(self, tags):
        """Search conversations by tags"""
        cursor = self.db.cursor()
        placeholders = ','.join(['?' for _ in tags])
        cursor.execute(f"""
            SELECT h.*, GROUP_CONCAT(ct.tag) as tags FROM history h
            JOIN conversation_tags ct ON h.id = ct.conversation_id
            WHERE ct.tag IN ({placeholders})
            GROUP BY h.id
        """, tags)
        return cursor.fetchall()
    
    def auto_tag_conversation(self, conversation_id, content):
        """Auto-generate tags using simple keyword extraction"""
        # Simple keyword extraction
        keywords = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        common_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 'which', 'their', 'time', 'about'}
        
        # Get most frequent non-common words
        word_freq = {}
        for word in keywords:
            if word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Add top 3 words as tags
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        for word, freq in top_words:
            if freq > 2:  # Only if word appears more than twice
                self.add_tag(conversation_id, word)