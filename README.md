AI Mentor ChatbotThis project is a production-ready, role-based AI Mentor Chatbot built with Streamlit. It allows users to log in, start learning sessions on any topic, and receive tailored guidance from an AI that adapts its teaching style based on the user's role (e.g., Executive, Analyst).FeaturesSecure User Authentication: Users must log in to access the application.Session Management: Start new learning sessions or resume previous conversations.Role-Based AI Mentoring: The AI's personality and teaching style adapt to the user's professional role.Centralized Prompt Management: All AI prompts are managed in an external prompts.yaml file for easy updates.Text & Audio Input: Interact with the mentor via typed text or voice transcription.Text-to-Speech Output: The mentor's responses are spoken aloud.Production-Ready Structure: Clean, modular, and well-documented codebase.Project Structurerole_based_agents/
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
Setup and InstallationClone the Repository:git clone <your-repo-url>
cd role_based_agents
Create a Virtual Environment:python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
Install Dependencies:pip install -r requirements.txt
You may also need to install ffmpeg for the audio transcription functionality:# On macOS
brew install ffmpeg

# On Windows (using Chocolatey)
choco install ffmpeg

# On Debian/Ubuntu
sudo apt update && sudo apt install ffmpeg
Configure Environment Variables:Create a .env file in the project root and add your API keys. The connection.py is configured for Azure OpenAI, but you can adapt it to other providers.# .env
GPT4_API_KEY="your_azure_api_key"
GPT4_AZURE_ENDPOINT="your_azure_endpoint"
GPT4_API_VERSION="2024-02-15"
GPT4_DEPLOYMENT_NAME="your_deployment_name"
Initialize the Database:The application will automatically create the mentor.db file in the data/ directory on first run if it doesn't exist. You will need to add users to the users table manually using a DB browser or a separate script to enable login. A test user ('testuser' / 'password') is included in the database.py file for convenience.How to Run the ApplicationOnce the setup is complete, run the Streamlit application from the project's root directory:streamlit run mentor/ui/main.py
The application will open in your web browser.