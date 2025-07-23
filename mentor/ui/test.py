# mentor/ui/main.py

import streamlit as st
import json
import sys
import os
import time

# Adjusting the path to ensure shared modules are found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from shared.storage.handle_user import validate_login, get_user
from shared.storage.handle_mentor_chat_history import save_chat, get_chats, get_chat_messages
from mentor.core.engine.mentor_engine import MentorEngine

st.set_page_config(page_title="Mentor Me", layout="wide")

# Apply custom CSS for styling
st.markdown("""
<style>
/* [CSS styles omitted here for brevity – keep as in original] */
</style>
""", unsafe_allow_html=True)

def rerun_app():
    st.session_state["refresh_counter"] = st.session_state.get("refresh_counter", 0) + 1
    st.rerun()

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_chat_title" not in st.session_state:
    st.session_state.current_chat_title = None
if "input_message" not in st.session_state:
    st.session_state.input_message = ""
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0
if "learning_goal" not in st.session_state:
    st.session_state.learning_goal = ""
if "show_new_session_ui" not in st.session_state:
    st.session_state.show_new_session_ui = True
if "voice_input_active" not in st.session_state:
    st.session_state.voice_input_active = False
if "session_just_started" not in st.session_state:
    st.session_state.session_just_started = False

engine = MentorEngine()

# --- LOGIN SCREEN ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color: #007bff;'>Welcome to Mentor Me</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #555;'>Your personal AI learning assistant</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        user_id = st.text_input("Username", placeholder="Enter your user ID", key="login_user_id")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Login", use_container_width=True, key="login_button"):
            if validate_login(user_id, password):
                st.session_state.authenticated = True
                st.session_state.user_id = user_id
                rerun_app()
            else:
                st.error("Invalid credentials. Please try again.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"<div class='sidebar-user'>Logged in as: <strong>{st.session_state.user_id}</strong></div>", unsafe_allow_html=True)
    st.markdown("---")

    if st.button("Start New Session", key="new_session_button", use_container_width=True):
        st.session_state.current_chat_title = None
        st.session_state.chat_history = []
        st.session_state.learning_goal = ""
        st.session_state.input_message = ""
        st.session_state.show_new_session_ui = True
        st.session_state.voice_input_active = False
        st.session_state.session_just_started = False
        rerun_app()

    st.markdown("---")
    st.subheader("Your Learning History")
    chats = get_chats(st.session_state.user_id)
    if chats:
        sorted_chats = sorted(chats, key=lambda x: x[2], reverse=True)
        for chat_id, title, created in sorted_chats:
            button_key = f"chat_select_{chat_id}_{st.session_state.refresh_counter}"
            display_title = f"{title[:35]}{'...' if len(title) > 35 else ''}"
            display_date = f"{created[:10]}"
            button_label = f"{display_title}\n{display_date}"

            if st.button(button_label, key=button_key, use_container_width=True):
                st.session_state.current_chat_title = title
                messages_json = get_chat_messages(chat_id)
                if messages_json:
                    st.session_state.chat_history = json.loads(messages_json)
                st.session_state.learning_goal = title
                st.session_state.input_message = ""
                st.session_state.show_new_session_ui = False
                st.session_state.voice_input_active = False
                st.session_state.session_just_started = False
                rerun_app()
    else:
        st.info("No previous sessions found.")

# --- MAIN CONTENT ---
st.title("AI Mentor Assistant")

if st.session_state.show_new_session_ui and not st.session_state.current_chat_title:
    st.markdown("## Your Learning Journey Starts Here!")
    st.markdown("Tell your AI Mentor what you're excited to learn about today.")

    # New UI: Skill selection, difficulty, and user role
    predefined_skills = ["Python", "Data Science", "Web Development", "Machine Learning", "Cybersecurity"]
    selected_skills = st.multiselect("Choose your skills or interests:", predefined_skills)
    custom_skills = st.text_input("Other skills you'd like to add:", placeholder="e.g., Prompt Engineering, SQL")
    
    difficulty = st.selectbox("Select your difficulty level:", ["Beginner", "Intermediate", "Advanced"])
    user_role = st.selectbox("What's your role?", ["Student", "Professional", "Career Changer", "Other"])

    learning_goal_input = st.text_area("What's your learning goal?", height=150, key="learning_goal_input", placeholder="e.g., 'Understand the basics of quantum computing'")

    if st.button("Start Learning Session", use_container_width=True, key="start_session_button", disabled=not learning_goal_input.strip()):
        if learning_goal_input.strip() != st.session_state.learning_goal:
            st.session_state.learning_goal = learning_goal_input.strip()
            st.session_state.current_chat_title = None
            st.session_state.chat_history = []
            st.session_state.input_message = ""
            st.session_state.session_just_started = False

        with st.spinner("Generating mentor introduction and topics..."):
            all_skills = selected_skills + ([custom_skills] if custom_skills else [])
            skills_str = ", ".join(all_skills)

            context_description = (
                f"Learning Goal: {st.session_state.learning_goal}\n"
                f"Skills/Interests: {skills_str}\n"
                f"Difficulty: {difficulty}\n"
                f"User Role: {user_role}"
            )

            extra_instructions = (
                "You are a mentor who is very interactive. Ask questions, quiz the user, summarize lessons, and check understanding."
            )
            intro, topics = engine.generate_intro_and_topics(
                context_description,
                extra_instructions=extra_instructions
            )
            topic_list = "\n".join([f"- {t}" for t in topics])
            mentor_initial_message_content = (
                f"{intro}\n\nBased on your goal of **{st.session_state.learning_goal}**, here are the topics we'll explore:\n\n{topic_list}\n\nFeel free to ask questions anytime. Are you ready to begin?"
            )

            st.session_state.chat_history = [
                {"role": "assistant", "content": mentor_initial_message_content}
            ]
            st.session_state.current_chat_title = st.session_state.learning_goal
            st.session_state.show_new_session_ui = False
            st.session_state.session_just_started = True

            save_chat(
                user_id=st.session_state.user_id,
                title=st.session_state.current_chat_title,
                messages_json=json.dumps(st.session_state.chat_history, indent=2)
            )

        rerun_app()
    st.stop()

# (remaining session/chat UI continues unchanged)
# [...]
# --- Chat UI and Messaging ---

chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"<div style='text-align: right; color: black; background-color: #dcf8c6; padding: 10px; border-radius: 8px; margin: 5px 0;'>{message['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align: left; color: black; background-color: #f1f0f0; padding: 10px; border-radius: 8px; margin: 5px 0;'>{message['content']}</div>", unsafe_allow_html=True)

# --- Input box ---
st.markdown("---")
user_input = st.text_input("Type your message:", value=st.session_state.input_message, key="input_message_box", placeholder="Ask your mentor a question...", label_visibility="collapsed")

if st.button("➤", key="send_button", use_container_width=True) and user_input.strip():
    user_message = user_input.strip()
    st.session_state.chat_history.append({"role": "user", "content": user_message})
    st.session_state.input_message = ""

    with st.spinner("Mentor is replying..."):
        response = engine.chat(
            chat_history=st.session_state.chat_history,
            user_id=st.session_state.user_id
        )

        st.session_state.chat_history.append({"role": "assistant", "content": response})

        # Persist chat
        save_chat(
            user_id=st.session_state.user_id,
            title=st.session_state.current_chat_title,
            messages_json=json.dumps(st.session_state.chat_history, indent=2)
        )

    rerun_app()
