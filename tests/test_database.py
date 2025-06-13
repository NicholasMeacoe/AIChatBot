import pytest
import sqlite3
import json
import html
from datetime import datetime, timedelta

# Assuming database.py functions might use current_app from Flask for config (e.g., DB_NAME)
# or that init_db needs an app_context.
# from flask import current_app # Not strictly needed if conftest.py correctly patches config.DB_NAME

from database import (
    init_db, # Though called by app fixture, can be tested for idempotency or directly if needed
    save_chat_history,
    get_chat_history,
    get_distinct_chat_dates,
    delete_history_by_date,
    # get_db # Not explicitly tested, but used by other functions
)

# Helper function to get a raw DB connection for assertions
def get_raw_db_connection(app_fixture):
    # Ensure this uses the DB_NAME from the app_fixture's config,
    # which is made available via monkeypatching config.DB_NAME in conftest.py
    # and then database.py imports config.DB_NAME.
    import config as app_config # Get the potentially monkeypatched config
    return sqlite3.connect(app_config.DB_NAME)

def test_init_db(app):
    """Test that the history table is created with correct columns."""
    # init_db is called by the 'app' fixture setup in conftest.py.
    # We just need to check the schema.
    with app.app_context(): # Ensure we are in an app context for current_app if used by DB functions
        conn = get_raw_db_connection(app)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(history)")
        columns = {row[1]: row[2] for row in cursor.fetchall()} # name: type
        conn.close()

        assert 'id' in columns
        assert columns['id'] == 'INTEGER' # Primary key is usually INTEGER
        assert 'timestamp' in columns
        assert columns['timestamp'] == 'DATETIME'
        assert 'user_message' in columns
        assert columns['user_message'] == 'TEXT'
        assert 'bot_response' in columns
        assert columns['bot_response'] == 'TEXT'
        assert 'context_info' in columns
        assert columns['context_info'] == 'TEXT' # Stored as JSON string

def test_save_chat_history(app):
    """Test saving a chat interaction."""
    with app.app_context():
        user_msg = "Hello <world>"
        bot_res = "Hi there >test<"
        context = [{"file": "test.txt", "status": "ok"}]

        assert save_chat_history(user_msg, bot_res, context) == True

        conn = get_raw_db_connection(app)
        cursor = conn.cursor()
        cursor.execute("SELECT user_message, bot_response, context_info FROM history WHERE user_message = ?", (user_msg,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == user_msg
        assert row[1] == bot_res
        assert json.loads(row[2]) == context

        # Test saving without context_info
        user_msg_no_context = "No context"
        bot_res_no_context = "Still no context"
        assert save_chat_history(user_msg_no_context, bot_res_no_context) == True

        conn = get_raw_db_connection(app)
        cursor = conn.cursor()
        cursor.execute("SELECT user_message, bot_response, context_info FROM history WHERE user_message = ?", (user_msg_no_context,))
        row_no_context = cursor.fetchone()
        conn.close()

        assert row_no_context is not None
        assert row_no_context[0] == user_msg_no_context
        assert row_no_context[1] == bot_res_no_context
        assert row_no_context[2] is None


def test_get_chat_history(app):
    """Test fetching chat history with various scenarios."""
    with app.app_context():
        # Setup some data
        now = datetime.utcnow()
        today_dt = now
        yesterday_dt = now - timedelta(days=1)

        today_str = today_dt.strftime('%Y-%m-%d')
        yesterday_str = yesterday_dt.strftime('%Y-%m-%d')

        # Raw inserts for precise timestamp control for testing
        conn = get_raw_db_connection(app)
        cursor = conn.cursor()
        # Insert in specific order to test sorting later
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       (yesterday_dt.strftime('%Y-%m-%d %H:%M:%S'), "Yesterday msg", "Bot yesterday"))
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       (today_dt.strftime('%Y-%m-%d %H:%M:%S'), "Today msg 1", "Bot today 1"))
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response, context_info) VALUES (?, ?, ?, ?)",
                       ((today_dt + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S'), "Today msg 2 <tag>", "Bot today 2 &", json.dumps([{"url":"http://example.com"}])))
        conn.commit()
        conn.close()

        # 1. Fetch all history
        all_history = get_chat_history()
        assert len(all_history) == 3
        assert all_history[0]['user_message'] == "Yesterday msg" # Check order (ASC by timestamp)
        assert all_history[1]['user_message'] == "Today msg 1"
        assert all_history[2]['user_message'] == html.escape("Today msg 2 <tag>")
        assert all_history[2]['bot_response'] == html.escape("Bot today 2 &")

        # 2. Fetch history for today
        today_history = get_chat_history(selected_date=today_str)
        assert len(today_history) == 2
        assert today_history[0]['user_message'] == "Today msg 1"
        assert today_history[1]['user_message'] == html.escape("Today msg 2 <tag>")

        # 3. Fetch history for a date with no entries
        future_date_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        future_history = get_chat_history(selected_date=future_date_str)
        assert len(future_history) == 0

        # 4. Fetch with invalid date format (should return all history as per database.py logic)
        invalid_date_history = get_chat_history(selected_date="invalid-date")
        # Current database.py logic prints an error and fetches all if date parsing fails
        assert len(invalid_date_history) == 3

    # 5. Test with empty database (need new app context for clean DB from fixture)
    # This requires the 'app' fixture to be function-scoped if we want it re-initialized.
    # However, 'app' is session-scoped. So, we manually clean for this part.
    with app.app_context():
        conn = get_raw_db_connection(app)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        conn.close()

        empty_history = get_chat_history()
        assert len(empty_history) == 0


def test_get_distinct_chat_dates(app):
    """Test fetching distinct chat dates."""
    with app.app_context():
        now = datetime.utcnow()
        today_dt = now
        yesterday_dt = now - timedelta(days=1)
        day_before_dt = now - timedelta(days=2)

        today_str = today_dt.strftime('%Y-%m-%d')
        yesterday_str = yesterday_dt.strftime('%Y-%m-%d')
        day_before_str = day_before_dt.strftime('%Y-%m-%d')

        # Scenario 1: No history (DB is clean at start of this test due to function scope or manual clean)
        conn = get_raw_db_connection(app)
        cursor = conn.cursor(); cursor.execute("DELETE FROM history"); conn.commit(); conn.close()
        assert get_distinct_chat_dates() == []

        # Scenario 2: History with multiple dates
        # save_chat_history uses current time, so good for today's entry
        save_chat_history("msg1_today", "res1_today")

        conn = get_raw_db_connection(app)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       (yesterday_dt.strftime('%Y-%m-%d %H:%M:%S'), "msg2_yesterday", "res2_yesterday"))
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       (day_before_dt.strftime('%Y-%m-%d %H:%M:%S'), "msg3_day_before", "res3_day_before"))
        # Add another for yesterday to ensure distinctness
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       ((yesterday_dt + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'), "msg4_yesterday_later", "res4_yesterday_later"))
        conn.commit()
        conn.close()

        dates = get_distinct_chat_dates()
        assert len(dates) == 3
        # Dates should be in descending order
        expected_dates_sorted = sorted([today_str, yesterday_str, day_before_str], reverse=True)
        assert dates == expected_dates_sorted

        # Scenario 3: History all on the same date
        conn = get_raw_db_connection(app)
        cursor = conn.cursor(); cursor.execute("DELETE FROM history"); conn.commit()
        save_chat_history("msg_today_1", "res_today_1") # Uses current time
        # Manually insert another with today's date but different time
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       ((today_dt - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'), "msg_today_2", "res_today_2"))
        conn.commit()
        conn.close()

        dates_same_day = get_distinct_chat_dates()
        assert len(dates_same_day) == 1
        assert dates_same_day == [today_str]


def test_delete_history_by_date(app):
    """Test deleting chat history by date."""
    with app.app_context():
        now = datetime.utcnow()
        today_dt = now
        yesterday_dt = now - timedelta(days=1)

        today_str = today_dt.strftime('%Y-%m-%d')
        yesterday_str = yesterday_dt.strftime('%Y-%m-%d')

        # Setup data
        conn = get_raw_db_connection(app)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history"); conn.commit() # Clean slate for this test

        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       (today_dt.strftime('%Y-%m-%d %H:%M:%S'), "Today msg 1", "Bot today 1"))
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       ((today_dt + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S'), "Today msg 2", "Bot today 2"))
        cursor.execute("INSERT INTO history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
                       (yesterday_dt.strftime('%Y-%m-%d %H:%M:%S'), "Yesterday msg", "Bot yesterday"))
        conn.commit()

        # 1. Delete history for today
        deleted_count_today = delete_history_by_date(today_str)
        assert deleted_count_today == 2

        remaining_history_today = get_chat_history(selected_date=today_str)
        assert len(remaining_history_today) == 0

        all_history_after_today_delete = get_chat_history()
        assert len(all_history_after_today_delete) == 1
        assert all_history_after_today_delete[0]['user_message'] == "Yesterday msg"

        # 2. Delete history for a date with no entries
        future_date_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        deleted_count_future = delete_history_by_date(future_date_str)
        assert deleted_count_future == 0

        # 3. Delete history for yesterday (remaining entry)
        deleted_count_yesterday = delete_history_by_date(yesterday_str)
        assert deleted_count_yesterday == 1
        assert len(get_chat_history()) == 0 # Now database should be empty

        # 4. Delete with invalid date format
        # database.py's delete_history_by_date prints error and returns 0 if date format is invalid
        deleted_count_invalid = delete_history_by_date("invalid-date-format")
        assert deleted_count_invalid == 0

        # 5. Delete from empty table (already tested by deleting all then trying to delete yesterday again)
        deleted_count_empty = delete_history_by_date(today_str) # Try deleting today again
        assert deleted_count_empty == 0
        conn.close() # Close connection at the end of test
