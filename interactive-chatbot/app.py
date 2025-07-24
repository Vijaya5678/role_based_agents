import streamlit as st
import sounddevice as sd
import numpy as np
import requests
import base64
import os
from utils import transcribe_audio, get_gpt_response, text_to_speech

# --- Page Configuration ---
st.set_page_config(
    page_title="Interactive AI Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Styling ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("static/styles.css")


# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "audio_data" not in st.session_state:
    st.session_state.audio_data = []


# --- UI Components ---
st.title("Interactive AI Chatbot")
st.markdown("Engage with the bot via text or live audio.")

# --- Chat History Display ---
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# --- User Input Section ---
input_container = st.container()
with input_container:
    user_input = st.chat_input("Type your message here...")
    
    col1, col2 = st.columns([0.8, 0.2])

    with col1:
        if st.button("Start Recording", key="start_rec"):
            st.session_state.is_recording = True
            st.session_state.audio_data = []
            st.info("Recording... Click 'Stop Recording' to finish.")

    with col2:
        if st.button("Stop Recording", key="stop_rec"):
            st.session_state.is_recording = False
            if st.session_state.audio_data:
                # Process the recorded audio
                samplerate = 44100  # Standard sample rate
                audio_np = np.concatenate(st.session_state.audio_data, axis=0)
                
                # Save as a temporary WAV file
                import soundfile as sf
                temp_audio_file = "temp_audio.wav"
                sf.write(temp_audio_file, audio_np, samplerate)

                # Transcribe the audio
                with st.spinner("Transcribing audio..."):
                    transcribed_text = transcribe_audio(temp_audio_file)
                
                if transcribed_text:
                    st.session_state.messages.append({"role": "user", "content": transcribed_text})
                    with st.chat_message("user"):
                        st.markdown(transcribed_text)
                    
                    # Get response from GPT
                    with st.spinner("Thinking..."):
                        bot_response = get_gpt_response(transcribed_text)
                        st.session_state.messages.append({"role": "assistant", "content": bot_response})
                        with st.chat_message("assistant"):
                            st.markdown(bot_response)
                        
                        # Convert response to speech and play it
                        audio_response = text_to_speech(bot_response)
                        st.audio(audio_response, format="audio/mp3")

                os.remove(temp_audio_file) # Clean up the temp file


# --- Handle Text Input ---
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner("Thinking..."):
        bot_response = get_gpt_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
        with st.chat_message("assistant"):
            st.markdown(bot_response)
        
        audio_response = text_to_speech(bot_response)
        st.audio(audio_response, format="audio/mp3", start_time=0)


# --- Audio Recording Logic ---
def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    if st.session_state.is_recording:
        st.session_state.audio_data.append(indata.copy())

try:
    with sd.InputStream(callback=audio_callback, channels=1, samplerate=44100):
        # This keeps the stream open while the app is running
        st.empty() 
except Exception as e:
    st.error(f"Could not open audio stream: {e}")
