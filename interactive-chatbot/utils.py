import requests
import os
from openai import AzureOpenAI

# --- API Credentials ---
MINI_TRANSCRIBE_API_KEY = "8D1vUrpem1BGDNTe0DEwkE8R8zaoFNvNTVVyNmcC0uX7zPGKN7F2JQQJ99BGACHYHv6XJ3w3AAAAACOGgfUD"
MINI_TRANSCRIBE_ENDPOINT = "https://agenticai-jbr-hcl-resource.cognitiveservices.azure.com/openai/deployments/gpt-4o-mini-transcribe/audio/transcriptions?api-version=2025-03-01-preview"

MINI_TTS_API_KEY = "8D1vUrpem1BGDNTe0DEwkE8R8zaoFNvNTVVyNmcC0uX7zPGKN7F2JQQJ99BGACHYHv6XJ3w3AAAAACOGgfUD"
MINI_TTS_ENDPOINT = "https://agenticai-jbr-hcl-resource.cognitiveservices.azure.com/openai/deployments/gpt-4o-mini-tts/audio/speech?api-version=2025-03-01-preview"

GPT4_API_KEY = "3uKlerOLPUx8H9KbL4xFRS6CMEdLypweLEZtKEofxOc9oX2ceWPDJQQJ99AKACYeBjFXJ3w3AAABACOG3Dq1"
GPT4_AZURE_ENDPOINT = "https://demoopenaikey.openai.azure.com/"
GPT4_API_VERSION = "2024-12-01-preview"


def transcribe_audio(file_path):
    """
    Transcribes audio using the Mini Transcribe API.
    """
    headers = {
        "api-key": MINI_TRANSCRIBE_API_KEY,
    }
    with open(file_path, "rb") as audio_file:
        files = {"file": (os.path.basename(file_path), audio_file, "audio/wav")}
        try:
            response = requests.post(MINI_TRANSCRIBE_ENDPOINT, headers=headers, files=files)
            response.raise_for_status()
            return response.json().get("text", "")
        except requests.exceptions.RequestException as e:
            print(f"Error in transcription API call: {e}")
            return None


def get_gpt_response(text):
    """
    Gets a response from the GPT-4.1 API using the AzureOpenAI client.
    """
    try:
        client = AzureOpenAI(
            api_key=GPT4_API_KEY,
            api_version=GPT4_API_VERSION,
            azure_endpoint=GPT4_AZURE_ENDPOINT,
        )

        response = client.chat.completions.create(
            model="gpt-4.1",  # Your deployment name
            messages=[{"role": "user", "content": text}],
            temperature=0.7,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in GPT API call: {e}")
        return "Sorry, I'm having trouble connecting to my brain right now."


def text_to_speech(text):
    """
    Converts text to speech using the Mini-tts API.
    """
    headers = {
        "Content-Type": "application/json",
        "api-key": MINI_TTS_API_KEY,
    }
    data = {"model": "tts-1", "input": text, "voice": "alloy"}
    try:
        response = requests.post(MINI_TTS_ENDPOINT, headers=headers, json=data)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error in TTS API call: {e}")
        return None
