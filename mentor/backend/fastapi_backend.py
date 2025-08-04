import os
import sys
import json
import datetime
import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple

# Adjusting system path to locate necessary modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'storage')))

# Importing custom modules for database operations and the core engine
from shared.storage.handle_user import validate_login
from shared.storage.handle_mentor_chat_history import (
    save_chat,
    get_chats,
    get_chat_messages_with_state,
    save_user_preferences,
    get_user_preferences,
    init_db
)
from mentor.core.engine.mentor_engine import MentorEngine

# Initialize the FastAPI application
app = FastAPI()

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """Initializes the database when the application starts."""
    init_db()
    print("Database initialized.")

# --- CORS Middleware ---
# Allows cross-origin requests, essential for web frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Instantiate the core mentor engine
engine = MentorEngine()

# --- Pydantic Models for Request Bodies ---
class LoginRequest(BaseModel):
    user_id: str
    password: str

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[float] = None
    audio_url: Optional[str] = None

# class ChatRequest(BaseModel):
#     user_id: str
#     chat_title: str
#     chat_history: List[ChatMessage]

class StartSessionRequest(BaseModel):
    user_id: str
    learning_goal: Optional[str] = None
    skills: List[str]
    difficulty: str
    role: str

class TopicPromptRequest(BaseModel):
    topic: str
    user_id: Optional[str] = None

class QuizRequest(BaseModel):
    user_id: str
    chat_title: str
    chat_history: List[ChatMessage]

class QuizAnswerRequest(BaseModel):
    user_id: str
    chat_title: str
    chat_history: List[ChatMessage]
    selected_option: str  # A, B, C, or D
    current_question_number: int

# Update your existing ChatRequest model to include quiz state
class ChatRequest(BaseModel):
    user_id: str
    chat_title: str
    chat_history: List[ChatMessage]
    is_quiz_mode: Optional[bool] = False
    quiz_state: Optional[dict] = None

# --- API Endpoints ---

@app.get("/")
async def read_root():
    """Root endpoint to check if the API is running."""
    return {"message": "Mentora Me API is running!"}

@app.post("/login")
async def login(req: LoginRequest):
    """Handles user login and validation."""
    print(f"-> /login called with user_id={req.user_id}")
    try:
        valid = validate_login(req.user_id, req.password)
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"success": True, "user_id": req.user_id}
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=404, detail="Login failed")

# @app.post("/start_session")
# async def start_session(req: StartSessionRequest):
#     """Starts a new learning session for a user."""
#     print(f"-> Starting session for user: {req.user_id}")
#     try:
#         # Save user preferences for the session
#         save_user_preferences(
#             user_id=req.user_id,
#             learning_goal=req.learning_goal,
#             skills=req.skills,
#             difficulty=req.difficulty,
#             role=req.role
#         )
#         print(f"Saved general preferences for user {req.user_id}")

#         # Build context for the mentor engine
#         context = (
#             f"Skills/Interests: {', '.join(req.skills)}\n"
#             f"Difficulty: {req.difficulty}\n"
#             f"User Role: {req.role}"
#         )
#         if req.learning_goal:
#             context = f"Learning Goal: {req.learning_goal}\n" + context

#         extra_instructions = (
#             "You are a mentor who is very interactive and strict to particular domain. if someone asked something which is not related to that domain. give fallback answer. ask questions, quiz the user, "
#             "summarize lessons, and check understanding."
#         )

#         # Generate introductory message and topics from the engine
#         intro, topics, suggestions = await engine.generate_intro_and_topics(
#             context_description=context,
#             extra_instructions=extra_instructions
#         )

#         initial_current_topic = topics[0] if topics else None
        
#         # Create a unique session title
#         base_title_part = req.learning_goal or (req.skills[0] if req.skills else "New Session")
#         sanitized_base_title = "".join(c for c in base_title_part if c.isalnum() or c == ' ').strip().replace(' ', '_')
#         if not sanitized_base_title:
#             sanitized_base_title = "Session"
#         session_title = f"{sanitized_base_title}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:4]}"

#         mentor_message_content = intro + "\n\nFeel free to ask questions anytime. Are you ready to begin?"
#         mentor_message_content = mentor_message_content.replace("🔊", "").strip()

#         # Create the initial message for the chat history
#         initial_chat_history_entry = ChatMessage(
#             role="assistant",
#             content=mentor_message_content,
#             timestamp=datetime.datetime.now().timestamp(),
#             audio_url=None
#         )

#         # Save the new chat session to the database
#         save_chat(
#             user_id=req.user_id,
#             title=session_title,
#             messages_json=json.dumps([initial_chat_history_entry.dict()]),
#             mentor_topics=topics,
#             current_topic=initial_current_topic,
#             completed_topics=[]
#         )

#         print(f"Session started successfully with title: {session_title}")
#         # Return all necessary information to the frontend
#         return {
#             "intro_and_topics": mentor_message_content,
#             "title": session_title,
#             "topics": topics,
#             "current_topic": initial_current_topic,
#             "suggestions": suggestions
#         }
#     except Exception as e:
#         print(f"X Error starting session: {e}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Could not start session: {str(e)}")


@app.post("/start_session")
async def start_session(req: StartSessionRequest):
    """Starts a new learning session for a user."""
    print(f"-> Starting session for user: {req.user_id}")
    try:
        # Save user preferences for the session
        save_user_preferences(
            user_id=req.user_id,
            learning_goal=req.learning_goal,
            skills=req.skills,
            difficulty=req.difficulty,
            role=req.role
        )
        print(f"Saved general preferences for user {req.user_id}")

        # Build context for the mentor engine
        context = (
            f"Skills/Interests: {', '.join(req.skills)}\n"
            f"Difficulty: {req.difficulty}\n"
            f"User Role: {req.role}"
        )
        if req.learning_goal:
            context = f"Learning Goal: {req.learning_goal}\n" + context

        extra_instructions = (
            "You are a mentor who is very interactive and strict to particular domain. if someone asked something which is not related to that domain. give fallback answer. ask questions, quiz the user, "
            "summarize lessons, and check understanding."
        )

        # Generate introductory message and topics from the engine with skills parameter
        intro, topics, suggestions = await engine.generate_intro_and_topics(
            context_description=context,
            extra_instructions=extra_instructions,
            role=req.role,
            skills=req.skills  # Pass skills to generate skills-based suggestions
        )

        initial_current_topic = topics[0] if topics else None
        
        # Create a unique session title
        base_title_part = req.learning_goal or (req.skills[0] if req.skills else "New Session")
        sanitized_base_title = "".join(c for c in base_title_part if c.isalnum() or c == ' ').strip().replace(' ', '_')
        if not sanitized_base_title:
            sanitized_base_title = "Session"
        session_title = f"{sanitized_base_title}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:4]}"

        mentor_message_content = intro + "\n\nFeel free to ask questions anytime. Are you ready to begin?"
        mentor_message_content = mentor_message_content.replace("🔊", "").strip()

        # Create the initial message for the chat history
        initial_chat_history_entry = ChatMessage(
            role="assistant",
            content=mentor_message_content,
            timestamp=datetime.datetime.now().timestamp(),
            audio_url=None
        )

        # Save the new chat session to the database
        save_chat(
            user_id=req.user_id,
            title=session_title,
            messages_json=json.dumps([initial_chat_history_entry.dict()]),
            mentor_topics=topics,
            current_topic=initial_current_topic,
            completed_topics=[]
        )

        print(f"Session started successfully with title: {session_title}")
        # Return all necessary information to the frontend
        return {
            "intro_and_topics": mentor_message_content,
            "title": session_title,
            "topics": topics,
            "current_topic": initial_current_topic,
            "suggestions": suggestions  # This will now contain your skills-based suggestions
        }
    except Exception as e:
        print(f"X Error starting session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not start session: {str(e)}")
    
# @app.post("/chat")
# async def chat(
#     self,
#     chat_history: List[Dict[str, Any]],
#     user_id: str,
#     chat_title: str,
#     learning_goal: Optional[str],
#     skills: List[str],
#     difficulty: str,
#     role: str,
#     mentor_topics: Optional[List[str]] = None,
#     current_topic: Optional[str] = None,
#     completed_topics: Optional[List[str]] = None,
#     is_quiz_mode: bool = False,
#     quiz_state: Optional[dict] = None,
# ) -> Tuple[str, List[str], Optional[dict]]:
#     if not chat_history:
#         return "Please start the conversation with a message.", [], None

#     summary = await self._get_conversation_summary(chat_title, chat_history)
#     recent_history = chat_history[-6:]

#     system_prompt = self._build_system_context(learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics)
#     messages_for_api = [{"role": "system", "content": system_prompt}]
    
#     if summary:
#         user_prompt_wrapper = self.prompts["tasks"]["chat"]["user_prompt_wrapper"]
#         messages_for_api.append({"role": "system", "content": user_prompt_wrapper.format(summary=summary)})

#     messages_for_api.extend(recent_history)

#     try:
#         llm_raw_response = await self._get_llm_completion(messages_for_api, temperature=0.7, max_tokens=1500, json_mode=True)
#         parsed = json.loads(llm_raw_response)
#         reply = self._sanitize_output(parsed.get("reply", "I'm sorry, I couldn't form a proper reply."))
#         suggestions = [self._sanitize_output(s) for s in parsed.get("suggestions", [])]
        
#         # Add "Quiz me!" suggestion after 5 conversations (count user messages only)
#         user_message_count = len([msg for msg in chat_history if msg.get("role") == "user"])
#         if user_message_count >= 5 and not is_quiz_mode:
#             # Check if quiz suggestion is not already present
#             if not any("quiz" in s.lower() for s in suggestions):
#                 suggestions.append("Quiz me!")
        
#         return reply, suggestions, quiz_state
#     except json.JSONDecodeError as e:
#         print(f"CRITICAL: LLM failed to produce valid JSON. Error: {e}. Response: {llm_raw_response}")
#         return "I seem to be having trouble formatting my thoughts. Please try rephrasing your question.", [], quiz_state
#     except Exception as e:
#         print(f"Error in chat: {e}")
#         return "I'm sorry, I couldn't understand your question. Could you please rephrase it?", [], quiz_state

@app.post("/chat")
async def chat(req: ChatRequest):
    """Handles an ongoing chat conversation."""
    print(f"-> /chat called by user: {req.user_id} for chat: '{req.chat_title}'")
    try:
        # Retrieve current chat state from the database
        result = get_chat_messages_with_state(req.user_id, req.chat_title)
        if result is None or not isinstance(result, tuple) or len(result) != 2:
            print("get_chat_messages_with_state returned None or unexpected format!")
            chat_messages, state = [], {}
        else:
            chat_messages, state = result

        # Extract session state and user preferences
        mentor_topics = state.get("mentor_topics", [])
        current_topic = state.get("current_topic")
        completed_topics = state.get("completed_topics", [])
        quiz_state = state.get("quiz_state", {}) if req.quiz_state is None else req.quiz_state
        
        prefs = get_user_preferences(req.user_id)
        learning_goal = prefs.get("learning_goal")
        skills = prefs.get("skills", [])
        difficulty = prefs.get("difficulty", "medium")
        role = prefs.get("role", "student")

        # Pass all necessary context, including quiz information, to the engine
        reply, suggestions, updated_quiz_state = await engine.chat(
            chat_history=[msg.dict() for msg in req.chat_history],
            user_id=req.user_id,
            chat_title=req.chat_title,
            learning_goal=learning_goal,
            skills=skills,
            difficulty=difficulty,
            role=role,
            mentor_topics=mentor_topics,
            current_topic=current_topic,
            completed_topics=completed_topics,
            is_quiz_mode=req.is_quiz_mode or False,
            quiz_state=quiz_state
        )

        # Create the new assistant message object
        mentor_message = ChatMessage(
            role="assistant",
            content=reply,
            timestamp=datetime.datetime.now().timestamp(),
            audio_url=None
        )

        # Update and save the chat history
        updated_history = req.chat_history + [mentor_message]
        
        # Update state if quiz state changed
        if updated_quiz_state is not None:
            state["quiz_state"] = updated_quiz_state
        
        save_chat(
            user_id=req.user_id,
            title=req.chat_title,
            messages_json=json.dumps([msg.dict() for msg in updated_history]),
            mentor_topics=mentor_topics,
            current_topic=current_topic,
            completed_topics=completed_topics,
            quiz_state=state.get("quiz_state")  # Save quiz state if present
        )

        # Return both reply and suggestions to the frontend
        response = {
            "reply": reply, 
            "suggestions": suggestions
        }
        
        # Include quiz state if present
        if updated_quiz_state:
            response["quiz_state"] = updated_quiz_state
            response["is_quiz_mode"] = updated_quiz_state.get("is_active", False)
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail="Chat failed")
    
@app.get("/get_chats")
async def list_chats(user_id: str = Query(..., description="User ID")):
    """Retrieves a list of all past chat sessions for a user."""
    print(f"-> /get_chats called for user_id='{user_id}'")
    try:
        chats = get_chats(user_id)
        return {"chats": chats}
    except Exception as e:
        print(f"Error getting chats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chats")

@app.get("/get_chat_messages")
async def get_chat_messages_route(user_id: str = Query(..., description="User ID"), title: str = Query(..., description="Chat Title")):
    """Retrieves all messages and state for a specific chat session."""
    print(f"-> /get_chat_messages called with user_id='{user_id}', title='{title}'")
    try:
        result = get_chat_messages_with_state(user_id, title)
        if result is None or not isinstance(result, tuple) or len(result) != 2:
            print("get_chat_messages_with_state returned None or unexpected format!")
            messages, state = [], {}
        else:
            messages, state = result
        return {"messages": messages, "state": state}
    except Exception as e:
        print(f"Error getting chat messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat messages")

# @app.post("/get_topic_prompts")
# async def get_topic_prompts(req: TopicPromptRequest):
#     """Generates suggested user prompts for a given topic."""
#     try:
#         prefs = get_user_preferences(req.user_id) if req.user_id else {}
#         context = ""
#         if prefs:
#             context = f"Learning Goal: {prefs.get('learning_goal','')}\nSkills: {', '.join(prefs.get('skills',[]))}\nDifficulty: {prefs.get('difficulty','')}\nRole: {prefs.get('role','')}"
#         prompts = await engine.generate_topic_prompts(req.topic, context_description=context)
#         return {"prompts": prompts}
#     except Exception as e:
#         # Fallback prompts in case of an error
#         return {"prompts": [
#             f"Can you explain {req.topic}?",
#             f"What are the key concepts of {req.topic}?",
#             f"What are the basics of {req.topic}?",
#             f"Can you give me a real-world example of {req.topic}?",
#             f"How do I apply {req.topic} in practice?"
#         ]}


# Add these new endpoints to your FastAPI app

@app.post("/start_quiz")
async def start_quiz(req: QuizRequest):
    """Starts a quiz based on conversation history."""
    print(f"-> /start_quiz called by user: {req.user_id} for chat: '{req.chat_title}'")
    try:
        # Get user preferences and chat state
        result = get_chat_messages_with_state(req.user_id, req.chat_title)
        if result is None or not isinstance(result, tuple) or len(result) != 2:
            chat_messages, state = [], {}
        else:
            chat_messages, state = result

        mentor_topics = state.get("mentor_topics", [])
        prefs = get_user_preferences(req.user_id)
        learning_goal = prefs.get("learning_goal")
        skills = prefs.get("skills", [])
        difficulty = prefs.get("difficulty", "medium")
        role = prefs.get("role", "student")

        # Start the quiz
        reply, suggestions, quiz_state = await engine.start_quiz(
            chat_history=[msg.dict() for msg in req.chat_history],
            user_id=req.user_id,
            chat_title=req.chat_title,
            learning_goal=learning_goal,
            skills=skills,
            difficulty=difficulty,
            role=role,
            mentor_topics=mentor_topics
        )

        # Create quiz message
        quiz_message = ChatMessage(
            role="assistant",
            content=reply,
            timestamp=datetime.datetime.now().timestamp(),
            audio_url=None
        )

        # Update chat history with quiz state
        updated_history = req.chat_history + [quiz_message]
        
        # Save with quiz state
        extended_state = state.copy()
        extended_state["quiz_state"] = quiz_state
        
        save_chat(
            user_id=req.user_id,
            title=req.chat_title,
            messages_json=json.dumps([msg.dict() for msg in updated_history]),
            mentor_topics=mentor_topics,
            current_topic=state.get("current_topic"),
            completed_topics=state.get("completed_topics", []),
            quiz_state=quiz_state  # You may need to modify save_chat to handle this
        )

        return {
            "reply": reply,
            "suggestions": suggestions,
            "quiz_state": quiz_state,
            "is_quiz_mode": True
        }
    except Exception as e:
        print(f"Error starting quiz: {e}")
        raise HTTPException(status_code=500, detail="Failed to start quiz")

@app.post("/quiz_answer")
async def quiz_answer(req: QuizAnswerRequest):
    """Handles quiz answer evaluation."""
    print(f"-> /quiz_answer called by user: {req.user_id}")
    try:
        # Get current state
        result = get_chat_messages_with_state(req.user_id, req.chat_title)
        if result is None or not isinstance(result, tuple) or len(result) != 2:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        chat_messages, state = result
        quiz_state = state.get("quiz_state", {})
        
        if not quiz_state.get("is_active", False):
            raise HTTPException(status_code=400, detail="No active quiz found")

        # Get user preferences
        mentor_topics = state.get("mentor_topics", [])
        prefs = get_user_preferences(req.user_id)
        learning_goal = prefs.get("learning_goal")
        skills = prefs.get("skills", [])
        difficulty = prefs.get("difficulty", "medium")
        role = prefs.get("role", "student")

        # Handle the quiz answer
        reply, suggestions, updated_quiz_state = await engine.handle_quiz_answer(
            chat_history=[msg.dict() for msg in req.chat_history],
            selected_option=req.selected_option,
            quiz_state=quiz_state,
            user_id=req.user_id,
            chat_title=req.chat_title,
            learning_goal=learning_goal,
            skills=skills,
            difficulty=difficulty,
            role=role,
            mentor_topics=mentor_topics
        )

        # Create response message
        response_message = ChatMessage(
            role="assistant",
            content=reply,
            timestamp=datetime.datetime.now().timestamp(),
            audio_url=None
        )

        # Update chat history
        updated_history = req.chat_history + [response_message]
        
        # Update state
        extended_state = state.copy()
        extended_state["quiz_state"] = updated_quiz_state
        
        save_chat(
            user_id=req.user_id,
            title=req.chat_title,
            messages_json=json.dumps([msg.dict() for msg in updated_history]),
            mentor_topics=mentor_topics,
            current_topic=state.get("current_topic"),
            completed_topics=state.get("completed_topics", []),
            quiz_state=updated_quiz_state
        )

        return {
            "reply": reply,
            "suggestions": suggestions,
            "quiz_state": updated_quiz_state,
            "is_quiz_mode": updated_quiz_state.get("is_active", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error handling quiz answer: {e}")
        raise HTTPException(status_code=500, detail="Failed to process quiz answer")