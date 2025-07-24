from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import sys
import os

# Add shared module path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Internal imports
from shared.storage.handle_user import validate_login
from shared.storage.handle_mentor_chat_history import save_chat, get_chats, get_chat_messages
from mentor.core.engine.mentor_engine import MentorEngine

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = MentorEngine()

# Data Models

class LoginRequest(BaseModel):
    user_id: str
    password: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    user_id: str
    chat_history: List[ChatMessage]

class StartSessionRequest(BaseModel):
    # Removed learning_goal since frontend dropped it?
    # But your current backend uses it, so keep for now.
    user_id: str
    learning_goal: Optional[str] = None  # Optional if frontend removes it
    skills: List[str]
    difficulty: str
    role: str

class SaveChatRequest(BaseModel):
    user_id: str
    title: str
    messages_json: str

# Routes

@app.post("/login")
def login(req: LoginRequest):
    print(f"➡️ /login called with user_id={req.user_id}")
    try:
        if validate_login(req.user_id, req.password):
            print(f"✅ Login success for user_id={req.user_id}")
            return {"success": True}
        else:
            print(f"❌ Invalid login attempt for user_id={req.user_id}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        print(f"💥 Error during login: {e}")
        raise HTTPException(status_code=500, detail="Server error during login")

@app.post("/chat")
def chat(req: ChatRequest):
    print(f"💬 /chat called by user: {req.user_id}")
    try:
        chat_history_dicts = [msg.dict() for msg in req.chat_history]
        response = engine.chat(
            chat_history=chat_history_dicts,
            user_id=req.user_id
        )
        return {"reply": response}
    except Exception as e:
        print(f"💥 Error during chat: {e}")
        raise HTTPException(status_code=500, detail="Chat failed")

@app.post("/start_session")
def start_session(req: StartSessionRequest):
    print(f"🚀 Starting session for user: {req.user_id}")
    try:
        context = (
            f"Skills/Interests: {', '.join(req.skills)}\n"
            f"Difficulty: {req.difficulty}\n"
            f"User Role: {req.role}"
        )
        # If learning_goal is still used, you can append or modify context here:
        if req.learning_goal:
            context = f"Learning Goal: {req.learning_goal}\n" + context

        extra_instructions = (
            "You are a mentor who is very interactive. Ask questions, quiz the user, summarize lessons, and check understanding."
        )

        intro, topics = engine.generate_intro_and_topics(
            context_description=context,
            extra_instructions=extra_instructions
        )

        topic_list = "\n".join([f"- {t}" for t in topics])
        mentor_message = (
            f"{intro}\n\nHere are the topics we'll explore:\n\n{topic_list}\n\nFeel free to ask questions anytime. Are you ready to begin?"
        )

        return {
            "intro_and_topics": mentor_message,
            "title": req.learning_goal or "New Session",
        }
    except Exception as e:
        print(f"💥 Error starting session: {e}")
        raise HTTPException(status_code=500, detail="Could not start session")

@app.get("/get_chats")
def list_chats(user_id: str):
    print(f"📚 /get_chats called for user_id={user_id}")
    try:
        chats = get_chats(user_id)
        # Expected return format:
        # chats = [
        #   [id, preview, timestamp],
        #   ...
        # ]
        return {"chats": chats}
    except Exception as e:
        print(f"💥 Error fetching chat list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chats")

@app.get("/get_chat_messages")
def get_chat_messages_route(user_id: str, chat_id: int = Query(..., description="Chat ID")):
    print(f"📥 /get_chat_messages called with user_id={user_id}, chat_id={chat_id}")
    try:
        # Your existing get_chat_messages function expects title; now use chat_id
        # Adjust your storage layer accordingly if needed
        messages_json = get_chat_messages(chat_id)  # Pass chat_id (int) instead of title (str)
        if messages_json:
            return {"messages": json.loads(messages_json)}
        else:
            return {"messages": []}
    except Exception as e:
        print(f"💥 Error retrieving messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat messages")

@app.post("/save-chat")
def save_chat_route(req: SaveChatRequest):
    print(f"💾 Saving chat for user_id={req.user_id} with title={req.title}")
    try:
        save_chat(
            user_id=req.user_id,
            title=req.title,
            messages_json=req.messages_json
        )
        return {"success": True}
    except Exception as e:
        print(f"💥 Error saving chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to save chat")
