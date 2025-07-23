# File: interview_bot/app.py
import streamlit as st
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from config.master_data import (
    CATEGORIES, ROLE_MAPPING, QUESTION_OPTIONS, 
    DURATION_OPTIONS, DIFFICULTY_LEVELS, ROLE_DISPLAY_NAMES
)
from core.interview_engine import InterviewEngine

# Page configuration
st.set_page_config(
    page_title="Interview Assistant",
    page_icon="🗪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling (cleaned up)
st.markdown("""
<style>
    /* Main styling */
    .main-header {
        text-align: center;
        color: #2c3e50;
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .sub-header {
        text-align: center;
        color: #7f8c8d;
        font-size: 1.3rem;
        margin-bottom: 3rem;
        font-weight: 400;
    }
    
    /* Timer styling */
    .timer-container {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(231, 76, 60, 0.3);
    }
    
    .timer-text {
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        border: none;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    
    /* Section headers */
    .section-header {
        color: #2c3e50;
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #3498db;
    }
    
    /* Chat styling for better formatting */
    .stChatMessage {
        padding: 0.5rem;
        margin: 0.5rem 0;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if "interview_engine" not in st.session_state:
        st.session_state.interview_engine = InterviewEngine()
    if "interview_stage" not in st.session_state:
        st.session_state.interview_stage = "welcome"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "interview_params" not in st.session_state:
        st.session_state.interview_params = {}
    if "interview_start_time" not in st.session_state:
        st.session_state.interview_start_time = None

def reset_interview():
    """Reset the entire interview"""
    st.session_state.interview_engine.reset_interview()
    st.session_state.interview_stage = "welcome"
    st.session_state.chat_history = []
    st.session_state.interview_params = {}
    st.session_state.interview_start_time = None

def get_remaining_time():
    """Calculate remaining interview time"""
    if not st.session_state.interview_start_time:
        return 0
    
    duration_minutes = st.session_state.interview_params.get("duration", 30)
    elapsed = datetime.now() - st.session_state.interview_start_time
    remaining = (duration_minutes * 60) - elapsed.total_seconds()
    return max(0, remaining)

def format_time(seconds):
    """Format seconds into MM:SS"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def main():
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">Interview Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional Skills Assessment Platform</p>', unsafe_allow_html=True)
    
    # Sidebar for interview controls
    with st.sidebar:
        st.markdown('<div class="section-header">Interview Controls</div>', unsafe_allow_html=True)
        
        if st.button("Start New Interview", type="primary", use_container_width=True):
            reset_interview()
            st.rerun()
        
        # Show current interview progress if in progress
        if hasattr(st.session_state.interview_engine, 'questions') and st.session_state.interview_engine.questions:
            progress = st.session_state.interview_engine.get_interview_progress()
            
            st.markdown('<div class="section-header">Progress</div>', unsafe_allow_html=True)
            st.progress(progress["progress"] / 100)
            st.write(f"Question {progress['current']} of {progress['total']}")
            
            # Show interview parameters
            if st.session_state.interview_params:
                st.markdown('<div class="section-header">Interview Details</div>', unsafe_allow_html=True)
                params = st.session_state.interview_params
                st.write(f"**Role:** {params.get('role', '').replace('_', ' ').title()}")
                st.write(f"**Category:** {params.get('category', '').title()}")
                st.write(f"**Difficulty:** {params.get('difficulty', '').title()}")
                st.write(f"**Duration:** {params.get('duration', 0)} minutes")
    
    # Main content area
    if st.session_state.interview_stage == "welcome":
        show_welcome_screen()
    elif st.session_state.interview_stage == "setup":
        show_setup_screen()
    elif st.session_state.interview_stage == "interview":
        show_interview_screen()

def show_welcome_screen():
    """Show welcome screen with bot introduction"""
    st.markdown("### Welcome to Interview Assistant")
    
    welcome_message = """
    This is your AI-powered interview assistant designed to assess your professional skills through interactive conversations.
    
    **How it works:**
    1. **Configure Parameters** - Choose your role, difficulty level, and interview duration
    2. **Interactive Assessment** - Answer questions in a natural conversational format
    3. **Real-time Feedback** - Receive immediate evaluation and helpful guidance
    4. **Comprehensive Analysis** - Get detailed performance insights and recommendations
    
    **Key Features:**
    - Fair and constructive evaluation methodology
    - Intelligent hint system for challenging questions
    - Adaptive difficulty assessment
    - Professional feedback and recommendations
    
    **Available Assessment Areas:**
    - **Technical Roles:** Python Developer, Data Scientist, AI/ML Engineer, Full Stack Developer, DevOps Engineer, Software Architect
    - **Non-Technical Roles:** HR Manager, Project Manager, Business Analyst, Product Manager, Marketing Manager, Sales Executive
    
    Ready to begin your professional skills assessment?
    """
    
    st.markdown(welcome_message)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Begin Interview Setup", type="primary", use_container_width=True):
            st.session_state.interview_stage = "setup"
            st.rerun()

def show_setup_screen():
    """Show interview parameter setup screen"""
    st.markdown('<div class="section-header">Interview Configuration</div>', unsafe_allow_html=True)
    st.markdown("Configure your interview parameters for a personalized assessment experience.")
    
    # Category selection outside form for dynamic updates
    category = st.selectbox(
        "Assessment Category",
        CATEGORIES,
        format_func=lambda x: x.replace('_', ' ').title(),
        help="Select the primary focus area for your skills assessment",
        key="category_select"
    )
    
    # Handle category changes
    if "previous_category" not in st.session_state:
        st.session_state.previous_category = category
    
    if category != st.session_state.previous_category:
        st.session_state.previous_category = category
        st.rerun()
    
    # Main configuration form
    with st.form("interview_setup"):
        st.markdown("### Assessment Parameters")
        
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            available_roles = ROLE_MAPPING[category]
            role = st.selectbox(
                "Professional Role",
                available_roles,
                format_func=lambda x: ROLE_DISPLAY_NAMES.get(x, x.replace('_', ' ').title()),
                help="Choose the specific role for targeted assessment",
                key="role_select"
            )
            
            num_questions = st.selectbox(
                "Number of Questions",
                QUESTION_OPTIONS,
                index=1,
                help="Total questions for the assessment session"
            )
        
        with col2:
            difficulty = st.selectbox(
                "Difficulty Level",
                DIFFICULTY_LEVELS,
                index=1,
                format_func=lambda x: x.title(),
                help="Choose appropriate difficulty based on your experience level"
            )
            
            duration = st.selectbox(
                "Session Duration (minutes)",
                DURATION_OPTIONS,
                index=2,
                help="Maximum time allocated for the interview"
            )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("Start Assessment", type="primary", use_container_width=True)
        
        if submitted:
            st.session_state.interview_params = {
                "category": category,
                "role": role,
                "difficulty": difficulty,
                "num_questions": num_questions,
                "duration": duration
            }
            
            with st.spinner("Generating personalized assessment questions..."):
                try:
                    welcome_msg = st.session_state.interview_engine.start_interview(
                        category, role, difficulty, num_questions, duration
                    )
                    
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": welcome_msg
                    })
                    
                    st.session_state.interview_stage = "interview"
                    st.session_state.interview_start_time = datetime.now()
                    st.success("Assessment initialized successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to initialize assessment: {str(e)}")

def show_interview_screen():
    """Show the main interview chat interface"""
    # Get remaining time first
    remaining_seconds = get_remaining_time() if st.session_state.interview_start_time else 0
    
    # Check if time has expired and handle completion
    if st.session_state.interview_start_time and remaining_seconds <= 0 and not st.session_state.interview_engine.completed:
        # Time expired - mark interview as completed and show summary
        st.session_state.interview_engine.completed = True
        summary = st.session_state.interview_engine._generate_final_summary()
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"**Time Expired!** The interview has ended.\n\n{summary}"
        })
    
    # Timer display
    if st.session_state.interview_start_time:
        if remaining_seconds > 0:
            st.markdown(f'''
            <div class="timer-container">
                <div>Time Remaining</div>
                <div class="timer-text">{format_time(remaining_seconds)}</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="timer-container" style="background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);">
                <div>Time Expired</div>
                <div class="timer-text">00:00</div>
            </div>
            ''', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Assessment Session</div>', unsafe_allow_html=True)
    
    # Chat messages using Streamlit's built-in chat components
    chat_container = st.container()
    with chat_container:
        # for message in st.session_state.chat_history:
        #     if message["role"] == "user":
        #         with st.chat_message("user"):
        #             st.markdown(message["content"])
        #     else:
        #         with st.chat_message("assistant"):
        #             st.markdown(message["content"])
        # In the chat container
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant"):
                # Ensure proper markdown rendering for summaries
                    st.markdown(message["content"], unsafe_allow_html=False)

    
    # Check if interview is completed
    if st.session_state.interview_engine.completed:
        st.success("Assessment completed!")
        
        if st.button("Start New Assessment", type="primary", use_container_width=True):
            reset_interview()
            st.rerun()
        return
    
    # Input area (only show if interview is still active)
    col1, col2 = st.columns([4, 1], gap="medium")
    
    with col1:
        user_input = st.text_area(
            "Your Response:",
            height=120,
            placeholder="Type your answer here...",
            key="user_input",
            help="Provide your response to the current question"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")
        
        if st.button("Submit Response", type="primary", use_container_width=True):
            if user_input and user_input.strip():
                # Add user message to chat
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input
                })
                
                # Get bot response
                with st.spinner("Evaluating response..."):
                    if user_input.lower().strip() == "yes" and len(st.session_state.chat_history) == 2:
                        bot_response = st.session_state.interview_engine.get_current_question()
                    else:
                        bot_response = st.session_state.interview_engine.evaluate_answer(user_input)
                
                # Add bot response to chat
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": bot_response
                })
                
                # Clear the input field by deleting the session state key
                if "user_input" in st.session_state:
                    del st.session_state.user_input
                st.rerun()
        
        if st.button("Request Hint", use_container_width=True):
            hint = st.session_state.interview_engine.provide_hint()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": hint
            })
            st.rerun()
    
    # Action buttons
    st.markdown("---")
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        if st.button("Skip Current Question", use_container_width=True):
            st.session_state.chat_history.append({
                "role": "user",
                "content": "Skip this question"
            })
            
            skip_response = st.session_state.interview_engine._skip_to_next_question(
                "Moving to the next question as requested."
            )
            
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": skip_response
            })
            st.rerun()
    
    with col2:
        if st.button("Restart Assessment", use_container_width=True):
            reset_interview()
            st.rerun()

    # Auto-refresh timer - FIXED: Simple 1-second refresh when interview is active
    if (st.session_state.interview_start_time and 
        not st.session_state.interview_engine.completed):
        # Use a placeholder to create auto-refresh without blocking
        placeholder = st.empty()
        with placeholder:
            time.sleep(1)
        st.rerun()

    """Show the main interview chat interface"""
    # Timer display
    if st.session_state.interview_start_time:
        remaining_seconds = get_remaining_time()
        if remaining_seconds > 0:
            st.markdown(f'''
            <div class="timer-container">
                <div>Time Remaining</div>
                <div class="timer-text">{format_time(remaining_seconds)}</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="timer-container" style="background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);">
                <div>Time Expired</div>
                <div class="timer-text">00:00</div>
            </div>
            ''', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Assessment Session</div>', unsafe_allow_html=True)
    
    # Chat messages using Streamlit's built-in chat components
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(message["content"])
    
    # Check if interview is completed
    if st.session_state.interview_engine.completed:
        st.success("Assessment completed successfully!")
        
        if st.button("Start New Assessment", type="primary", use_container_width=True):
            reset_interview()
            st.rerun()
        return
    
    # Input area
    col1, col2 = st.columns([4, 1], gap="medium")
    
    with col1:
        user_input = st.text_area(
            "Your Response:",
            height=120,
            placeholder="Type your answer here...",
            key="user_input",
            help="Provide your response to the current question"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")
        
        if st.button("Submit Response", type="primary", use_container_width=True):
            if user_input and user_input.strip():
                # Add user message to chat
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input
                })
                
                # Get bot response
                with st.spinner("Evaluating response..."):
                    if user_input.lower().strip() == "yes" and len(st.session_state.chat_history) == 2:
                        bot_response = st.session_state.interview_engine.get_current_question()
                    else:
                        bot_response = st.session_state.interview_engine.evaluate_answer(user_input)
                
                # Add bot response to chat
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": bot_response
                })
                
                # Clear the input field by deleting the session state key
                del st.session_state.user_input
                st.rerun()
        
        if st.button("Request Hint", use_container_width=True):
            hint = st.session_state.interview_engine.provide_hint()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": hint
            })
            st.rerun()
    
    # Action buttons
    st.markdown("---")
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        if st.button("Skip Current Question", use_container_width=True):
            st.session_state.chat_history.append({
                "role": "user",
                "content": "Skip this question"
            })
            
            skip_response = st.session_state.interview_engine._skip_to_next_question(
                "Moving to the next question as requested."
            )
            
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": skip_response
            })
            st.rerun()
    
    with col2:
        if st.button("Restart Assessment", use_container_width=True):
            reset_interview()
            st.rerun()

    # Auto-refresh timer every 5 seconds to avoid too frequent updates
    if (st.session_state.interview_start_time and 
        not st.session_state.interview_engine.completed and 
        remaining_seconds > 0):
        time.sleep(0.1)  # Small delay to prevent excessive CPU usage
        if int(remaining_seconds) % 5 == 0:  # Update every 5 seconds
            st.rerun()

if __name__ == "__main__":
    main()
