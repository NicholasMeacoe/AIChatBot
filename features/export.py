import json
import markdown
from datetime import datetime
from io import BytesIO
import uuid

class ExportManager:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def export_conversation(self, conversation_id, format_type="markdown"):
        """Export conversation in specified format"""
        if format_type == "markdown":
            return self._export_markdown(conversation_id)
        elif format_type == "json":
            return self._export_json(conversation_id)
        elif format_type == "html":
            return self._export_html(conversation_id)
    
    def _export_markdown(self, conversation_id=None):
        """Export as Markdown"""
        cursor = self.db.cursor()
        if conversation_id:
            cursor.execute("SELECT * FROM history WHERE id = ?", (conversation_id,))
        else:
            cursor.execute("SELECT * FROM history ORDER BY timestamp")
        
        messages = cursor.fetchall()
        md_content = f"# Chat Export - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        for msg in messages:
            md_content += f"## User ({msg['timestamp']})\n{msg['user_message']}\n\n"
            md_content += f"## Assistant\n{msg['bot_response']}\n\n---\n\n"
        
        return md_content
    
    def _export_json(self, conversation_id=None):
        """Export as JSON"""
        cursor = self.db.cursor()
        if conversation_id:
            cursor.execute("SELECT * FROM history WHERE id = ?", (conversation_id,))
        else:
            cursor.execute("SELECT * FROM history ORDER BY timestamp")
        
        messages = [dict(row) for row in cursor.fetchall()]
        return json.dumps({
            "export_date": datetime.now().isoformat(),
            "messages": messages
        }, indent=2)
    
    def _export_html(self, conversation_id=None):
        """Export as HTML"""
        md_content = self._export_markdown(conversation_id)
        html_content = markdown.markdown(md_content)
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Chat Export</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .user {{ background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .assistant {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
        """
    
    def create_share_link(self, conversation_id):
        """Create shareable link for conversation"""
        share_id = str(uuid.uuid4())
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO shared_conversations (share_id, conversation_id, created_at)
            VALUES (?, ?, ?)
        """, (share_id, conversation_id, datetime.now()))
        self.db.commit()
        return share_id