# fastapi_backend.py

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import sys
import os
import io
import datetime
import uuid # For generating unique chat titles

# Add shared module path
# This assumes the directory structure:
# your_project/
# ├── mentor/
# │   ├── backend/
# │   │   └── fastapi_backend.py (this file)
# │   └── core/
# │       └── engine/
# │           ├── mentor_engine.py
# │           └── utils.py
# └── shared/
#     └── storage/
#         ├── handle_user.py
#         └── handle_mentor_chat_history.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'storage')))


# Internal imports
from shared.storage.handle_user import validate_login
from shared.storage.handle_mentor_chat_history import (
    save_chat,
    get_chats,
    get_chat_messages_with_state, # Correctly import this for state
    save_user_preferences,
    get_user_preferences,
    init_db # Ensure your DB is initialized at app startup
)

# Import MentorEngine from its specific path
from mentor.core.engine.mentor_engine import MentorEngine

# Import audio functions from your utils.py
# It is CRUCIAL that transcribe_audio and text_to_speech are defined as 'async def'
from mentor.core.engine.utils import transcribe_audio, text_to_speech

app = FastAPI()

# Initialize the database when the application starts
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized.")


# Enable CORS (Cross-Origin Resource Sharing)
# IMPORTANT: In production, replace allow_origins=["*"] with specific origins
# e.g., allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development. Be specific in production.
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Initialize your MentorEngine instance
# If MentorEngine's init now uses Connection internally to get its LLM client from .env,
# then passing api_key might be redundant. If not, you might need to re-add.
engine = MentorEngine() # Assuming MentorEngine's __init__ is now self-sufficient with its Connection.py

# --- Data Models ---

class LoginRequest(BaseModel):
    user_id: str
    password: str

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[float] = None # Unix timestamp (seconds since epoch)
    audio_url: Optional[str] = None # URL to an audio file for this message

class ChatRequest(BaseModel):
    user_id: str
    chat_title: str # <-- CRUCIAL: Identifies the ongoing chat session
    chat_history: List[ChatMessage] # Typically contains the full history including the latest user message

class StartSessionRequest(BaseModel):
    user_id: str
    learning_goal: Optional[str] = None # The user's specific goal, now optional
    skills: List[str] # Skills/interests from the user
    difficulty: str # Difficulty level chosen by the user
    role: str # User's role (e.g., "student", "developer")

class SaveChatRequest(BaseModel):
    user_id: str
    title: str # Title of the chat session
    messages_json: str # JSON string of the chat messages

class TTSRequest(BaseModel): # For the POST /text_to_speech endpoint
    text: str # The text content to convert to speech

# --- Routes ---

@app.get("/")
async def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {"message": "Mentor Me API is running!"}

@app.post("/login")
async def login(req: LoginRequest):
    """
    Handles user login.
    """
    print(f"-> /login called with user_id={req.user_id}")
    try:
        if validate_login(req.user_id, req.password):
            print(f"V Login success for user_id={req.user_id}")
            return {"success": True}
        else:
            print(f"X Invalid login attempt for user_id={req.user_id}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        print(f"X Error during login: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        raise HTTPException(status_code=500, detail="Server error during login")

@app.post("/start_session")
async def start_session(req: StartSessionRequest):
    """
    Initiates a new mentor session, generating an introduction and topics.
    Saves general user preferences and the initial session state.
    Returns the generated chat_title which the frontend must store.
    """
    print(f"-> Starting session for user: {req.user_id}")
    try:
        # 1. Save general user preferences
        save_user_preferences(
            user_id=req.user_id,
            learning_goal=req.learning_goal,
            skills=req.skills,
            difficulty=req.difficulty,
            role=req.role
        )
        print(f"Saved general preferences for user {req.user_id}")

        # 2. Generate intro and session topics using MentorEngine
        context = (
            f"Skills/Interests: {', '.join(req.skills)}\n"
            f"Difficulty: {req.difficulty}\n"
            f"User Role: {req.role}"
        )
        if req.learning_goal:
            context = f"Learning Goal: {req.learning_goal}\n" + context

        extra_instructions = (
            "You are a mentor who is very interactive. Ask questions, quiz the user, "
            "summarize lessons, and check understanding."
        )

        intro, topics = await engine.generate_intro_and_topics( # Await this call
            context_description=context,
            extra_instructions=extra_instructions
        )

        # 3. Prepare initial mentor message and session title
        initial_current_topic = topics[0] if topics else None
        # Generate a unique and user-friendly title for the session
        base_title_part = req.learning_goal or (req.skills[0] if req.skills else "New Session")
        # Sanitize base_title_part for use in a file/db key (replace spaces, remove special chars)
        sanitized_base_title = "".join(c for c in base_title_part if c.isalnum() or c == ' ').strip().replace(' ', '_')
        # Ensure it's not empty, fallback to "Session"
        if not sanitized_base_title:
            sanitized_base_title = "Session"
        session_title = f"{sanitized_base_title}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:4]}"

        # --- FIX APPLIED HERE ---
        # The 'intro' generated by the engine already contains the greeting and the topic list.
        # So, we just use 'intro' directly for the mentor_message_content.
        # We also explicitly remove the "🔊" from the initial message here, as per your request,
        # ensuring the backend sends it without the icon for the very first message.
        mentor_message_content = intro + "\n\nFeel free to ask questions anytime. Are you ready to begin?"
        # If the engine itself adds the 🔊, you might need a regex replace here:
        mentor_message_content = mentor_message_content.replace("🔊", "").strip() # Ensure no trailing spaces if 🔊 was at the end
        # --- FIX ENDS HERE ---

        initial_chat_history_entry = ChatMessage(
            role="assistant",
            content=mentor_message_content,
            timestamp=datetime.datetime.now().timestamp(),
            audio_url=None # Initially no audio URL
        )

        # 4. Save the initial chat message and session-specific topic state
        # The save_chat function is synchronous, no await needed here unless you change it
        save_chat(
            user_id=req.user_id,
            title=session_title, # Save with the generated unique title
            messages_json=json.dumps([initial_chat_history_entry.dict()]),
            mentor_topics=topics,           # Save generated topics for this session
            current_topic=initial_current_topic,  # Save initial current topic
            completed_topics=[]             # Initialize as empty
        )

        print(f"Session started successfully with title: {session_title}")
        return {
            "intro_and_topics": mentor_message_content, # Frontend will display this
            "title": session_title, # <-- CRUCIAL: RETURN THE GENERATED UNIQUE TITLE
            "topics": topics,
            "current_topic": initial_current_topic
        }
    except Exception as e:
        print(f"X Error starting session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not start session: {str(e)}")

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Handles ongoing chat interaction with the mentor engine.
    Loads and updates all necessary chat history and session state.
    The 'chat_title' from the request body identifies the specific session.
    """
    print(f"-> /chat called by user: {req.user_id} for chat: '{req.chat_title}'")
    try:
        # 1. Retrieve general user preferences
        user_prefs = get_user_preferences(req.user_id)
        if not user_prefs:
            raise HTTPException(status_code=400, detail="User preferences not found. Please start a session first.")

        current_learning_goal = user_prefs.get("learning_goal")
        current_skills = user_prefs.get("skills", [])
        current_difficulty = user_prefs.get("difficulty")
        current_role = user_prefs.get("role")

        if not current_skills or not current_difficulty or not current_role:
             raise HTTPException(status_code=500, detail="Incomplete user preferences loaded.")

        # 2. Retrieve session-specific state (chat messages, mentor_topics, current_topic, completed_topics)
        # Use req.chat_title to fetch the correct session
        session_state = get_chat_messages_with_state(user_id=req.user_id, chat_title=req.chat_title)

        if not session_state:
            raise HTTPException(status_code=400, detail=f"Chat session '{req.chat_title}' not found. Please start a new session or provide a valid chat title.")

        chat_history_json_from_db = session_state.get("messages_json")
        current_mentor_topics = session_state.get("mentor_topics", [])
        current_current_topic = session_state.get("current_topic")
        current_completed_topics = session_state.get("completed_topics", [])

        loaded_chat_history = json.loads(chat_history_json_from_db) if chat_history_json_from_db else []

        # Ensure the user's latest message (from req.chat_history) is properly formatted
        # and appended to the history loaded from the DB before sending to the engine.
        user_message_from_request = req.chat_history[-1].dict() if req.chat_history else None
        if user_message_from_request:
            # Append the new user message from the request to the loaded history
            combined_chat_history_for_engine = loaded_chat_history + [user_message_from_request]
        else:
            combined_chat_history_for_engine = loaded_chat_history

        print(f"Loaded session state for '{req.chat_title}': Current Topic='{current_current_topic}'")

        # 3. Call the MentorEngine to get a reply
        response_text = await engine.chat( # Await this call
            chat_history=combined_chat_history_for_engine, # Pass the full history including latest user message
            user_id=req.user_id,
            learning_goal=current_learning_goal,
            skills=current_skills,
            difficulty=current_difficulty,
            role=current_role,
            mentor_topics=current_mentor_topics,
            current_topic=current_current_topic,
            completed_topics=current_completed_topics
        )

        # 4. Update and save the chat history with the new mentor reply
        new_mentor_message = ChatMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.datetime.now().timestamp(),
            audio_url=None # No audio URL initially for mentor replies
        ).dict()

        # Add the latest user message and the new mentor reply to the history loaded from DB
        updated_chat_history_list = loaded_chat_history
        if user_message_from_request:
            updated_chat_history_list.append(user_message_from_request)
        updated_chat_history_list.append(new_mentor_message)

        # Save the updated full chat history and retain the topic state.
        # The save_chat function is synchronous, no await needed here unless you change it
        save_chat(
            user_id=req.user_id,
            title=req.chat_title, # <-- Use the chat_title from the request to save to the correct session
            messages_json=json.dumps(updated_chat_history_list),
            mentor_topics=current_mentor_topics, # Retain current topics for the session
            current_topic=current_current_topic, # Retain current topic
            completed_topics=current_completed_topics # Retain completed topics
        )

        return {"reply": response_text}
    except HTTPException:
        raise # Re-raise HTTPExceptions that we explicitly raise
    except Exception as e:
        print(f"X Error during chat: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Chat failed")

@app.get("/get_chats")
async def list_chats(user_id: str = Query(..., description="User ID")):
    """
    Retrieves a list of all chat sessions (title, creation timestamp) for a given user.
    """
    print(f"-> /get_chats called for user_id='{user_id}'")
    try:
        chats_data = get_chats(user_id) # Returns [[id, title, created_at_iso_str], ...]
        transformed_chats = []
        for chat_id, chat_title, created_at_iso_str in chats_data:
            try:
                # Ensure the created_at_iso_str is correctly parsed to a float timestamp
                created_at_dt = datetime.datetime.fromisoformat(created_at_iso_str)
                timestamp_float = created_at_dt.timestamp()
            except (ValueError, TypeError):
                # Fallback for old/malformed timestamps - use current time
                timestamp_float = datetime.datetime.now().timestamp()

            # Frontend expects [title, preview_text, timestamp]
            # For now, using chat_title for preview text. You might want to get
            # a snippet from the first or last message for a more meaningful preview.
            transformed_chats.append([
                chat_title,   # This is the unique title that needs to be sent back to /chat
                chat_title,   # Placeholder for preview, ideally a message snippet
                timestamp_float
            ])
        return {"chats": transformed_chats}
    except Exception as e:
        print(f"X Error fetching chat list: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to get chats")

@app.get("/get_chat_messages")
async def get_chat_messages_route(user_id: str = Query(..., description="User ID"), title: str = Query(..., description="Chat Title")):
    """
    Retrieves all messages for a specific chat session, along with its associated state.
    The 'title' parameter is used to identify the chat.
    """
    print(f"-> /get_chat_messages called with user_id='{user_id}', title='{title}'")
    try:
        # Use get_chat_messages_with_state to retrieve messages and topic state
        session_data = get_chat_messages_with_state(user_id=user_id, chat_title=title)
        if session_data:
            messages_list = json.loads(session_data.get("messages_json", "[]"))
            # Return full state for frontend to manage
            return {
                "messages": messages_list,
                "mentor_topics": session_data.get("mentor_topics", []),
                "current_topic": session_data.get("current_topic"),
                "completed_topics": session_data.get("completed_topics", [])
            }
        # If no session data found, return empty lists
        return {"messages": [], "mentor_topics": [], "current_topic": None, "completed_topics": []}
    except Exception as e:
        print(f"X Error retrieving messages: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to get chat messages")

# NOTE: The /save-chat endpoint might become redundant if all saves are handled
# within /start_session and /chat. I'm keeping it for now if you have other uses.
@app.post("/save-chat")
async def save_chat_route(req: SaveChatRequest):
    """
    Saves or updates a chat session's history. (This might be redundant if /chat handles all updates)
    """
    print(f"-> Saving chat for user_id='{req.user_id}' with title='{req.title}' (direct save)")
    try:
        # This endpoint doesn't handle topic state, only message history.
        save_chat(
            user_id=req.user_id,
            title=req.title,
            messages_json=req.messages_json,
            # Pass None for topic state as this endpoint doesn't manage it
            mentor_topics=None,
            current_topic=None,
            completed_topics=None
        )
        return {"success": True}
    except Exception as e:
        print(f"X Error saving chat directly: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to save chat")


# --- AUDIO ENDPOINTS ---

@app.post("/transcribe_audio")
async def transcribe_audio_endpoint(audio: UploadFile = File(...)):
    """
    Transcribes an uploaded audio file to text using an async utility function.
    """
    print(f"-> /transcribe_audio called for file: {audio.filename}")
    if not audio.content_type or not audio.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only audio files are allowed.")

    try:
        audio_bytes = await audio.read() # Await needed for UploadFile.read()

        transcribed_text = await transcribe_audio(audio_bytes) # Await the async transcription

        if transcribed_text is None:
            raise HTTPException(status_code=500, detail="Transcription service returned an error or no text.")

        print(f"-> Transcribed text: {transcribed_text[:50]}...")
        return JSONResponse(content={"text": transcribed_text})
    except HTTPException:
        raise
    except Exception as e:
        print(f"X Error during audio transcription endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/text_to_speech")
async def text_to_speech_post_endpoint(req: TTSRequest):
    """
    Converts text to speech (POST method). Returns audio as a stream.
    """
    print(f"-> /text_to_speech (POST) called for text: {req.text[:50]}...")
    try:
        audio_content_bytes = await text_to_speech(req.text) # Await the async TTS

        if audio_content_bytes is None:
            raise HTTPException(status_code=500, detail="Text-to-speech service returned an error or no audio content.")
        if not audio_content_bytes: # Check for empty bytes
            raise HTTPException(status_code=500, detail="Text-to-speech generation failed (empty content).")

        return StreamingResponse(io.BytesIO(audio_content_bytes), media_type="audio/mp3")

    except HTTPException:
        raise
    except Exception as e:
        print(f"X Error during text-to-speech (POST) endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Text-to-speech failed: {str(e)}")

@app.get("/text_to_speech_direct")
async def text_to_speech_get_endpoint(text: str = Query(..., description="Text to convert to speech")):
    """
    Converts text to speech (GET method). Useful for direct URL playback.
    """
    print(f"-> /text_to_speech_direct (GET) called for text: {text[:50]}...")
    try:
        audio_content_bytes = await text_to_speech(text) # Await the async TTS

        if audio_content_bytes is None:
            raise HTTPException(status_code=500, detail="Text-to-speech service returned an error or no audio content.")
        if not audio_content_bytes:
            raise HTTPException(status_code=500, detail="Text-to-speech generation failed (empty content).")

        return StreamingResponse(io.BytesIO(audio_content_bytes), media_type="audio/mp3")
    except HTTPException:
        raise
    except Exception as e:
        print(f"X Error during text-to_speech_direct (GET) endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Text-to-speech failed: {str(e)}")