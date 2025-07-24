# mentor/backendn/utils.py
from typing import Optional
import os
import httpx # NEW: For asynchronous HTTP requests
from openai import AsyncAzureOpenAI # NEW: For asynchronous Azure OpenAI client
from dotenv import load_dotenv # NEW: For loading environment variables
import io # NEW: For handling audio bytes as file-like objects

# Load environment variables from .env file
load_dotenv()

# --- API Credentials (Now loaded from environment variables) ---
# Ensure these keys are set in your .env file:
# MINI_TRANSCRIBE_API_KEY="..."
# MINI_TRANSCRIBE_ENDPOINT="..."
# MINI_TTS_API_KEY="..."
# MINI_TTS_ENDPOINT="..."
# GPT4_API_KEY="..."
# GPT4_AZURE_ENDPOINT="..."
# GPT4_API_VERSION="..." # Make sure this is also in .env if it varies

MINI_TRANSCRIBE_API_KEY = os.getenv("MINI_TRANSCRIBE_API_KEY")
MINI_TRANSCRIBE_ENDPOINT = os.getenv("MINI_TRANSCRIBE_ENDPOINT")

MINI_TTS_API_KEY = os.getenv("MINI_TTS_API_KEY")
MINI_TTS_ENDPOINT = os.getenv("MINI_TTS_ENDPOINT")

GPT4_API_KEY = os.getenv("GPT4_API_KEY")
GPT4_AZURE_ENDPOINT = os.getenv("GPT4_AZURE_ENDPOINT")
GPT4_API_VERSION = os.getenv("GPT4_API_VERSION", "2024-12-01-preview") # Default if not set in .env


async def transcribe_audio(audio_bytes: bytes) -> Optional[str]:
    """
    Transcribes audio bytes using the Mini Transcribe API asynchronously.
    """
    headers = {
        "api-key": MINI_TRANSCRIBE_API_KEY,
    }
    # Create a file-like object from bytes for httpx to send
    files = {"file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(MINI_TRANSCRIBE_ENDPOINT, headers=headers, files=files, timeout=60.0) # Added timeout
            response.raise_for_status() # Raise an exception for bad status codes
            return response.json().get("text", "")
        except httpx.RequestError as e:
            print(f"Error in transcription API call: {e}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error in transcription API call: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"Unexpected error in transcription: {e}")
            return None


async def get_gpt_response(text: str) -> Optional[str]:
    """
    Gets a response from the GPT-4.1 API using the AsyncAzureOpenAI client.
    """
    try:
        client = AsyncAzureOpenAI( # Use AsyncAzureOpenAI
            api_key=GPT4_API_KEY,
            api_version=GPT4_API_VERSION,
            azure_endpoint=GPT4_AZURE_ENDPOINT,
        )

        response = await client.chat.completions.create( # Use await
            model="gpt-4.1",  # Your deployment name
            messages=[{"role": "user", "content": text}],
            temperature=0.7,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in GPT API call: {e}")
        return "Sorry, I'm having trouble connecting to my brain right now."


async def text_to_speech(text: str) -> Optional[bytes]:
    """
    Converts text to speech using the Mini-tts API asynchronously.
    """
    headers = {
        "Content-Type": "application/json",
        "api-key": MINI_TTS_API_KEY,
    }
    data = {"model": "tts-1", "input": text, "voice": "alloy"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(MINI_TTS_ENDPOINT, headers=headers, json=data, timeout=60.0) # Added timeout
            response.raise_for_status()
            return response.content
        except httpx.RequestError as e:
            print(f"Error in TTS API call: {e}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error in TTS API call: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"Unexpected error in TTS: {e}")
            return None