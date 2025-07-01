import sqlite3
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict

class AnalyticsManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.init_analytics_tables()
    
    def init_analytics_tables(self):
        """Initialize analytics tables"""
        cursor = self.db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                session_id TEXT
            )
        """)
        self.db.commit()
    
    def track_event(self, event_type, event_data=None, user_id=None, session_id=None):
        """Track analytics event"""
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO usage_analytics (event_type, event_data, user_id, session_id)
            VALUES (?, ?, ?, ?)
        """, (event_type, json.dumps(event_data) if event_data else None, user_id, session_id))
        self.db.commit()
    
    def get_usage_stats(self, days=30):
        """Get usage statistics for the last N days"""
        cursor = self.db.cursor()
        since_date = datetime.now() - timedelta(days=days)
        
        # Message count by day
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM history 
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (since_date,))
        daily_messages = cursor.fetchall()
        
        # Model usage
        cursor.execute("""
            SELECT event_data, COUNT(*) as count
            FROM usage_analytics 
            WHERE event_type = 'model_used' AND timestamp >= ?
            GROUP BY event_data
        """, (since_date,))
        model_usage = cursor.fetchall()
        
        # Context usage
        cursor.execute("""
            SELECT COUNT(*) as total_context_items
            FROM history 
            WHERE context_info IS NOT NULL AND timestamp >= ?
        """, (since_date,))
        context_usage = cursor.fetchone()
        
        return {
            'daily_messages': [{'date': row[0], 'count': row[1]} for row in daily_messages],
            'model_usage': [{'model': json.loads(row[0]) if row[0] else 'unknown', 'count': row[1]} for row in model_usage],
            'context_usage': context_usage[0] if context_usage else 0,
            'period_days': days
        }
    
    def get_conversation_insights(self, days=30):
        """Get insights about conversations"""
        cursor = self.db.cursor()
        since_date = datetime.now() - timedelta(days=days)
        
        # Get all messages
        cursor.execute("""
            SELECT user_message, bot_response, context_info
            FROM history 
            WHERE timestamp >= ?
        """, (since_date,))
        messages = cursor.fetchall()
        
        # Analyze topics
        topics = self._extract_topics_from_messages(messages)
        
        # Average message length
        user_msg_lengths = [len(msg[0]) for msg in messages if msg[0]]
        bot_msg_lengths = [len(msg[1]) for msg in messages if msg[1]]
        
        avg_user_length = sum(user_msg_lengths) / len(user_msg_lengths) if user_msg_lengths else 0
        avg_bot_length = sum(bot_msg_lengths) / len(bot_msg_lengths) if bot_msg_lengths else 0
        
        # Context effectiveness
        context_messages = [msg for msg in messages if msg[2]]
        context_effectiveness = len(context_messages) / len(messages) if messages else 0
        
        return {
            'top_topics': topics[:10],
            'avg_user_message_length': round(avg_user_length, 2),
            'avg_bot_message_length': round(avg_bot_length, 2),
            'context_usage_rate': round(context_effectiveness * 100, 2),
            'total_conversations': len(messages)
        }
    
    def _extract_topics_from_messages(self, messages):
        """Extract topics from message content"""
        import re
        
        all_text = ' '.join([msg[0] + ' ' + msg[1] for msg in messages if msg[0] and msg[1]])
        words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
        
        # Filter common words
        common_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 'which', 'their', 'time', 'about', 'code', 'file', 'help', 'need', 'want', 'like', 'know', 'think', 'please', 'thank', 'would', 'could', 'should'}
        
        filtered_words = [word for word in words if word not in common_words and len(word) > 4]
        word_counts = Counter(filtered_words)
        
        return [{'topic': word, 'count': count} for word, count in word_counts.most_common()]
    
    def get_productivity_metrics(self, days=30):
        """Get productivity insights"""
        cursor = self.db.cursor()
        since_date = datetime.now() - timedelta(days=days)
        
        # Messages per hour distribution
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM history 
            WHERE timestamp >= ?
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """, (since_date,))
        hourly_distribution = cursor.fetchall()
        
        # Most productive days
        cursor.execute("""
            SELECT strftime('%w', timestamp) as day_of_week, COUNT(*) as count
            FROM history 
            WHERE timestamp >= ?
            GROUP BY strftime('%w', timestamp)
            ORDER BY count DESC
        """, (since_date,))
        daily_distribution = cursor.fetchall()
        
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        return {
            'hourly_activity': [{'hour': int(row[0]), 'count': row[1]} for row in hourly_distribution],
            'daily_activity': [{'day': day_names[int(row[0])], 'count': row[1]} for row in daily_distribution],
            'peak_hour': max(hourly_distribution, key=lambda x: x[1])[0] if hourly_distribution else None
        }