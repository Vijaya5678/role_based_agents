import requests

BASE_URL = "http://127.0.0.1:8000"

# 1. Login
def test_login():
    print("🔐 Testing /login ...")
    data = {
        "user_id": "vijaya01",
        "password": "vijaya@123"
    }
    r = requests.post(f"{BASE_URL}/login", json=data)
    print(r.status_code, r.json())

# 2. Start Session
def test_start_session():
    print("🚀 Testing /start_session ...")
    data = {
        "user_id": "testuser",
        "learning_goal": "Learn FastAPI",
        "skills": ["Python", "APIs"],
        "difficulty": "Beginner",
        "role": "Developer"
    }
    r = requests.post(f"{BASE_URL}/start_session", json=data)
    print(r.status_code, r.json())
    return r.json().get("title", "Untitled Session")

# 3. Chat
def test_chat(title):
    print("💬 Testing /chat ...")
    data = {
        "user_id": "testuser",
        "chat_history": [
            {"role": "user", "content": "What is FastAPI?"}
        ]
    }
    r = requests.post(f"{BASE_URL}/chat", json=data)
    print(r.status_code, r.json())

# 4. Save Chat
def test_save_chat(title):
    print("💾 Testing /save-chat ...")
    data = {
        "user_id": "testuser",
        "title": title,
        "messages_json": '[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]'
    }
    r = requests.post(f"{BASE_URL}/save-chat", json=data)
    print(r.status_code, r.json())

# 5. Get Chats
def test_get_chats():
    print("📚 Testing /get_chats ...")
    r = requests.get(f"{BASE_URL}/get_chats", params={"user_id": "testuser"})
    print(r.status_code, r.json())

# 6. Get Chat Messages
def test_get_chat_messages(title):
    print("📨 Testing /get_chat_messages ...")
    r = requests.get(f"{BASE_URL}/get_chat_messages", params={
        "user_id": "testuser",
        "title": title
    })
    print(r.status_code, r.json())

# Run all tests
if __name__ == "__main__":
    test_login()
    session_title = test_start_session()
    test_chat(session_title)
    test_save_chat(session_title)
    test_get_chats()
    test_get_chat_messages(session_title)
