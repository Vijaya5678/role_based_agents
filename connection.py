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

        # Load optional transcription LLM config
        self.tt_provider = os.getenv("TT_LLM_PROVIDER", "openai")  # e.g., openai or azure
        self.tt_api_key = os.getenv("TT_LLM_API_KEY")
        self.tt_model = os.getenv("TT_LLM_MODEL", "gpt-4o-mini-transcribe")

        if not self.tt_api_key:
            print("⚠️ Transcription API key (TT_LLM_API_KEY) not found. Audio transcription won't work.")

        # Holders
        self.llm = None
        self.tt_llm = None

    def get_llm(self):
        if not self.llm:
            if self.provider == "gemini":
                self.llm = LLM(model="gemini/gemini-2.0-flash", provider="google")
            elif self.provider == "openai":
                self.llm = LLM(model="gpt-4o-mini", provider="openai")
        return self.llm

    def get_tt_llm(self):
        if not self.tt_api_key:
            raise ValueError("No API key found for transcription LLM")

        if not self.tt_llm:
            os.environ["OPENAI_API_KEY"] = self.tt_api_key  # Assuming OpenAI for now
            self.tt_llm = LLM(model=self.tt_model, provider=self.tt_provider)

        return self.tt_llm


if __name__ == "__main__":
    conn = Connection()
    llm = conn.get_llm()
    print("✅ Main LLM Response:", llm.call("Say hello!"))

    try:
        tt_llm = conn.get_tt_llm()
        print("✅ Transcription LLM Ready:", tt_llm.model)
    except Exception as e:
        print("⚠️ Transcription LLM not initialized:", e)
