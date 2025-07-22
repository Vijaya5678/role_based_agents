#gemini flash connetcion
# connection.py
# Gemini Flash connection (CrewAI)

import os
from crewai import LLM
from dotenv import load_dotenv

# Load .env file (if exists)
load_dotenv()

# Ensure the key is set
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment or .env file")

# Set the env variable for CrewAI
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

# Initialize LLM
llm = LLM(model="gemini/gemini-2.0-flash", provider="google")

# Quick test
if __name__ == "__main__":
    print(llm.call("Say hello!"))
