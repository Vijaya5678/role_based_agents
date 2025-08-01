
# AI Mentor Chatbot- Mentora

This project is a **production-ready, AI Mentor Chatbot** built with Html and FastAPI. It enables users to log in, initiate learning sessions, and receive tailored guidance from an AI that adapts its mentoring style based on the user's professional role (e.g., Executive, Technical).

---

## 🔧 Features

- **Secure User Authentication**: Login required to access the chatbot.
- **Session Management**: Resume or start new learning sessions.
- **Role-Based AI Mentoring**: Custom mentoring style for each user role.
- **Centralized Prompt Management**: All prompts are stored in `prompts.yaml`.
- **Text-to-Speech Output**: Mentor speaks the responses aloud.
- **Clean Architecture**: Modular, scalable, and production-ready codebase.

---

## 📁 Project Structure

```
role_based_agents/
├── data/
│   └── mentor_data.db  
│   ___ user_history.db                  # Centralized database
├── mentor/
│   ├── backend/
│   │   └── fastapi_backend.py       # FastAPI backend
│   ├── core/
│   │   └── engine/
│   │       ├── mentor_engine.py     # Core application logic
│   │       └── prompts.yaml         # All LLM prompts
│   ├── shared/
│   │   └── storage/
│   │       ├── create_user_data.py          # Setup user data
│   │       ├── handle_mentor_chat_history.py # Chat history operations
│   │       └── handle_user.py               # User authentication & management
│   └── ui/
│       ├── index.html              # UI template in html
│
├── connection.py                  # LLM connection logic 
├── .env                           # Environment variables
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 🚀 Setup and Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd role_based_agents
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```



### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
GPT4_API_KEY="your_azure_api_key"
GPT4_AZURE_ENDPOINT="your_azure_endpoint"
GPT4_API_VERSION="2024-02-15"
GPT4_DEPLOYMENT_NAME="your_deployment_name"
```

### 5. Initialize the Database

Run create_user_data.py to create `user_history.db` in the `data/` directory on the first run. To enable login, add users to the `users` table using a DB browser or script. A test user is included in `handle_user.py`:

```python
test_user = {'username': 'vijaya01', 'password': 'vijaya@123'}
```

---

## 🧠 How to Run the App

```bash
uvicorn fastapi_backend:app --reload --port 8084
```

Visit the local URL in your browser to interact with the chatbot.

---

## 📬 Feedback

For issues, suggestions, or contributions, feel free to open an issue or a PR on the repository.

---

© 2025 HCLTech Mentora
