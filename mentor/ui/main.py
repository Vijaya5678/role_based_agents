import streamlit as st
import datetime
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from shared.storage.handle_user import validate_login
from mentor.core.engine.mentor_engine import MentorEngine

st.set_page_config(page_title="Mentor Assistant", layout="wide")

# Initialize session state keys
for key, default in {
    "authenticated": False,
    "user_id": None,
    "chat_history": [],
    "current_chat_title": None,
    "input_message": "",
    "learning_goal": "",
    "refresh_counter": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

engine = MentorEngine()

def rerun_app():
    st.session_state.refresh_counter += 1

# --- LOGIN ---
if not st.session_state.authenticated:
    st.title("🔐 AI Mentor Me")
    user_id = st.text_input("User ID")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if validate_login(user_id, password):
            st.session_state.authenticated = True
            st.session_state.user_id = user_id
            rerun_app()
        else:
            st.error("Invalid credentials")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"<div style='margin-bottom:20px;'>👤 User: `{st.session_state.user_id}`</div>", unsafe_allow_html=True)
    st.subheader("📚 Past Sessions")

    def friendly_title(title_with_ts: str):
        return title_with_ts.rsplit(" - ", 1)[0] if " - " in title_with_ts else title_with_ts

    old_chats = engine.list_chats(st.session_state.user_id)

    if old_chats:
        for chat_title in old_chats:
            display_title = friendly_title(chat_title)
            if st.button(display_title, key=f"oldchat_{chat_title}"):
                chat_data = engine.load_chat(st.session_state.user_id, chat_title)
                if chat_data:
                    st.session_state.current_chat_title = chat_title
                    st.session_state.chat_history = chat_data.get("messages", [])
                    st.session_state.learning_goal = display_title.replace("Learning ", "")
                    st.session_state.input_message = ""
                    rerun_app()
                else:
                    st.warning("Could not load selected chat.")
    else:
        st.info("No previous sessions found.")

# --- MAIN UI ---
st.title("🎓 AI Mentor Assistant")

# Start new session if none active
if not st.session_state.current_chat_title:
    st.subheader("🧠 What do you want to learn today?")
    learning_desc = st.text_area("Describe your learning goals here...")

    if st.button("Start New Session"):
        if learning_desc.strip():
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
            new_title = f"Learning {learning_desc.strip()} - {timestamp}"

            st.session_state.learning_goal = learning_desc.strip()
            st.session_state.current_chat_title = new_title

            # Always generate fresh intro and topics
            title, messages, _ = engine.launch_mentor_session(
                user_id=st.session_state.user_id,
                learning_description=st.session_state.learning_goal,
                user_message=None,
                custom_title=new_title
            )
            st.session_state.chat_history = messages
            st.session_state.input_message = ""
            rerun_app()
        else:
            st.warning("Please enter your learning goals.")
    st.stop()

# Display chat title friendly (strip timestamp)
def strip_ts(title: str) -> str:
    return title.rsplit(" - ", 1)[0] if " - " in title else title

st.subheader(f"💬 Session: {strip_ts(st.session_state.current_chat_title)}")

# Show chat messages
chat_container = st.container()
with chat_container:
    st.markdown('<div style="max-height:600px; overflow-y:auto; padding:10px; border:1px solid #ddd; border-radius:6px;">', unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        bg_color = "#e0f7fa" if role == "mentor" else "#f1f8e9"
        align = "left" if role == "mentor" else "right"
        st.markdown(f'<div style="background-color:{bg_color}; padding:8px; margin:4px; border-radius:8px; max-width:80%; text-align:{align};">{content}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

st.text_area("Your Message", key="input_message", height=100, label_visibility="collapsed")

if st.button("Send"):
    msg = st.session_state.input_message.strip()
    if msg:
        with st.spinner("Mentor is typing..."):
            title, messages, reply = engine.launch_mentor_session(
                user_id=st.session_state.user_id,
                learning_description=st.session_state.learning_goal,
                user_message=msg,
                custom_title=st.session_state.current_chat_title
            )
            st.session_state.chat_history = messages
            st.session_state.input_message = ""
            rerun_app()
    else:
        st.warning("Please enter a message to send.")
