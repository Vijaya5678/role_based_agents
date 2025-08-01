import sqlite3
from datetime import datetime
import os



DATABASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
DATABASE_NAME = 'user_history.db'
DB_PATH = os.path.join(DATABASE_DIR, DATABASE_NAME)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# Drop and create users table
c.execute('DROP TABLE IF EXISTS users')
conn.commit()

c.execute('''
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    firm TEXT,
    unit TEXT,
    location TEXT,
    created_at TEXT NOT NULL
)
''')
conn.commit()

# Seed dummy users
dummy_users = [
    {
        "user_id": "vijaya01",
        "name": "Vijaya",
        "password": "vijaya@123",
        "email": "vijaya@hcl.com",
        "firm": "HCL",
        "unit": "AI & Analytics",
        "location": "Chennai"
    },
    {
        "user_id": "harish02",
        "name": "Harish",
        "password": "harish@123",
        "email": "harish@hcl.com",
        "firm": "HCL",
        "unit": "CloudOps",
        "location": "Bangalore"
    },
    {
        "user_id": "shivam03",
        "name": "Shivam",
        "password": "shivam@123",
        "email": "shivam@hcl.com",
        "firm": "HCL",
        "unit": "GENAI",
        "location": "Bangalore"
    },
    # add other users similarly...
]

now = datetime.utcnow().isoformat()

for user in dummy_users:
    c.execute('''
        INSERT INTO users (user_id, name, password, email, firm, unit, location, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user["user_id"], user["name"], user["password"], user["email"],
          user["firm"], user["unit"], user["location"], now))

conn.commit()
print("✅ Database initialized and dummy users created.")
