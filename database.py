import sqlite3
import json
import html
from datetime import datetime
from config import DB_NAME # Import database name from config

def init_db():
    """Initializes the database and creates the history table if it doesn't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                context_info TEXT NULL -- Store JSON string of context details
            )
        ''')
        conn.commit()
        # Access app config to check for TESTING mode
        from flask import current_app
        if not current_app or not current_app.config.get('TESTING'):
            print(f"Database '{DB_NAME}' initialized successfully.")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()

def get_db():
    """Establishes a connection to the database."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row # Return rows as dict-like objects
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None # Return None if connection fails

def save_chat_history(user_message, bot_response, context_info_list=None):
    """Saves a user message, bot response, and context info to the database."""
    conn = get_db()
    if not conn:
        return False # Cannot save if connection failed

    context_info_json = json.dumps(context_info_list) if context_info_list else None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (user_message, bot_response, context_info) VALUES (?, ?, ?)",
            (user_message, bot_response, context_info_json)
        )
        conn.commit()
        from flask import current_app # Ensure it's available in this scope
        if not current_app or not current_app.config.get('TESTING'):
            print(f"Saved interaction to DB: User: '{user_message[:50]}...', Bot: '{bot_response[:50]}...'")
        return True
    except sqlite3.Error as e:
        print(f"Database error saving chat history: {e}")
        return False
    finally:
        conn.close()

def get_chat_history(selected_date=None):
    """Fetches chat history, optionally filtered by date. Returns HTML-escaped data."""
    conn = get_db()
    if not conn:
        return [] # Return empty list if connection failed

    history_list = []
    try:
        cursor = conn.cursor()
        if selected_date:
            # Validate date format before querying
            try:
                datetime.strptime(selected_date, '%Y-%m-%d')
                cursor.execute(
                    "SELECT user_message, bot_response, timestamp FROM history WHERE DATE(timestamp) = ? ORDER BY timestamp ASC",
                    (selected_date,)
                )
            except ValueError:
                print(f"Invalid date format provided: {selected_date}. Fetching all history.")
                cursor.execute("SELECT user_message, bot_response, timestamp FROM history ORDER BY timestamp ASC")
        else:
            cursor.execute("SELECT user_message, bot_response, timestamp FROM history ORDER BY timestamp ASC")

        rows = cursor.fetchall()
        for row in rows:
            # HTML escape the data before returning
            history_list.append({
                'user_message': html.escape(row['user_message']),
                'bot_response': html.escape(row['bot_response']),
                'timestamp': row['timestamp']
            })
        return history_list
    except sqlite3.Error as e:
        print(f"Database error fetching chat history: {e}")
        return [] # Return empty list on error
    finally:
        conn.close()

def get_distinct_chat_dates():
    """Fetches distinct dates from the chat history."""
    conn = get_db()
    if not conn:
        return []

    dates = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT DATE(timestamp) as chat_date FROM history ORDER BY chat_date DESC")
        dates = [row['chat_date'] for row in cursor.fetchall()]
        return dates
    except sqlite3.Error as e:
        print(f"Database error fetching distinct dates: {e}")
        return []
    finally:
        conn.close()

def delete_history_by_date(date_str):
    """Deletes chat history for a specific date. Returns the number of deleted rows."""
    conn = get_db()
    if not conn:
        return 0 # Indicate failure or no deletion

    # Validate date format first
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(f"Invalid date format for deletion: {date_str}")
        return 0 # Return 0 as no rows will be deleted

    deleted_count = 0
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE DATE(timestamp) = ?", (date_str,))
        conn.commit()
        deleted_count = cursor.rowcount # Get the number of deleted rows
        print(f"Deleted {deleted_count} entries for date: {date_str}")
        return deleted_count
    except sqlite3.Error as e:
        print(f"Database error deleting history for {date_str}: {e}")
        return 0 # Return 0 on error
    finally:
        conn.close()

# Initialize the database when this module is imported (or run)
# init_db() # Consider calling this explicitly in app setup instead
