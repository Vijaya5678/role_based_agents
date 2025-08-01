
# AI Mentor Chatbot

This project is a **production-ready, role-based AI Mentor Chatbot** built with Streamlit. It enables users to log in, initiate learning sessions, and receive tailored guidance from an AI that adapts its mentoring style based on the user's professional role (e.g., Executive, Analyst).

---

## 🔧 Features

- **🔐 Secure User Authentication**: Login required to access the chatbot.
- **💬 Session Management**: Resume or start new learning sessions.
- **👔 Role-Based AI Mentoring**: Custom mentoring style for each user role.
- **📂 Centralized Prompt Management**: All prompts are stored in `prompts.yaml`.
- **🎙️ Text & Audio Input**: Ask questions via text or voice transcription.
- **🗣️ Text-to-Speech Output**: Mentor speaks the responses aloud.
- **🏗️ Clean Architecture**: Modular, scalable, and production-ready codebase.

---

## 📁 Project Structure

```
role_based_agents/
├── data/
│   └── mentor.db           # Centralized database
├── mentor/
│   ├── core/
│   │   ├── engine/
│   │   │   ├── connection.py     # Handles LLM connection
│   │   │   ├── mentor_engine.py  # Core application logic
│   │   │   └── prompts.yaml      # All LLM prompts
│   │   └── storage/
│   │       └── database.py       # Handles all DB operations
│   └── ui/
│       └── main.py             # Streamlit user interface
├── .env                      # Environment variables
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

You may also need to install `ffmpeg` for audio transcription:

```bash
# macOS
brew install ffmpeg

# Windows (with Chocolatey)
choco install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg
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

The app will auto-create `mentor.db` in the `data/` directory on the first run. To enable login, add users to the `users` table using a DB browser or script. A test user is included in `database.py`:

```python
test_user = {'username': 'testuser', 'password': 'password'}
```

---

## 🧠 How to Run the App

```bash
streamlit run mentor/ui/main.py
```

Visit the local URL in your browser to interact with the chatbot.

---

## 📬 Feedback

For issues, suggestions, or contributions, feel free to open an issue or a PR on the repository.

---

© 2025 AI Mentor Team
