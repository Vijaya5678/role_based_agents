import sqlite3

DB_PATH = "mentor_chat_history.db"

def init_learning_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_learning (
                user_id TEXT,
                skill TEXT,
                topic TEXT,
                level TEXT,
                status TEXT,  -- started, completed
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def mark_topic_learned(user_id, skill, topic, level):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_learning (user_id, skill, topic, level, status)
            VALUES (?, ?, ?, ?, 'completed')
        ''', (user_id, skill, topic, level))
        conn.commit()

def get_learned_topics(user_id, skill):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT topic FROM user_learning
            WHERE user_id = ? AND skill = ? AND status = 'completed'
        ''', (user_id, skill))
        return [row[0] for row in cursor.fetchall()]
