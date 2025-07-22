import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history_mentor.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    messages TEXT NOT NULL,
    created_at TEXT NOT NULL
)
''')
conn.commit()

def save_chat(user_id, title, messages_json):
    now = datetime.utcnow().isoformat()
    c.execute('INSERT INTO chats (user_id, title, messages, created_at) VALUES (?, ?, ?, ?)',
              (user_id, title, messages_json, now))
    conn.commit()
    return c.lastrowid

def get_chats(user_id):
    c.execute('SELECT id, title, created_at FROM chats WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return c.fetchall()

def get_chat_messages(chat_id):
    c.execute('SELECT messages FROM chats WHERE id = ?', (chat_id,))
    row = c.fetchone()
    return row[0] if row else None
