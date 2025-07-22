# connection.py
import os
from crewai import LLM
from dotenv import load_dotenv

class Connection:
    def __init__(self):
        load_dotenv()
        self.provider = os.getenv("LLM_PROVIDER", "gemini")  # 'gemini' or 'openai'
        self.api_key = os.getenv("GEMINI_API_KEY") if self.provider == "gemini" else os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError(f"API key not found for provider {self.provider}")

        if self.provider == "gemini":
            os.environ["GEMINI_API_KEY"] = self.api_key
        elif self.provider == "openai":
            os.environ["OPENAI_API_KEY"] = self.api_key
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        self.llm = None

    def get_llm(self):
        if not self.llm:
            if self.provider == "gemini":
                self.llm = LLM(model="gemini/gemini-2.0-flash", provider="google")
            elif self.provider == "openai":
                self.llm = LLM(model="gpt-4o-mini", provider="openai")
        return self.llm

if __name__ == "__main__":
    connection = Connection()
    llm = connection.get_llm()
    response = llm.call("Say hello!")
    print("✅ Successfully connected to LLM!")
    print("Response:", response)
