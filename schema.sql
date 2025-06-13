DROP TABLE IF EXISTS history;

CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT NOT NULL,
    bot_response TEXT,
    context_info TEXT -- Store as JSON string
);

-- Optional: Indexes for performance if the table grows large
-- CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history (timestamp);
-- CREATE INDEX IF NOT EXISTS idx_history_user_message ON history (user_message);
