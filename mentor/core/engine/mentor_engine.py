# mentor/core/engine/mentor_engine.py

import os
import json
import re
from crewai import LLM
from datetime import datetime
from typing import Optional
from crewai import Crew, Task
from mentor.core.agent.mentor_agent import create_mentor_agent
from connection import Connection


def safe_filename(title: str, max_length=100) -> str:
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    safe_title = safe_title.replace(" ", "_")
    if len(safe_title) > max_length:
        safe_title = safe_title[:max_length] + "..."
    return safe_title


class MentorEngine:
    def __init__(self):
        conn = Connection()
        self.llm = conn.get_llm()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.chat_dir = os.path.abspath(os.path.join(base_dir, "../../../data/chats"))
        os.makedirs(self.chat_dir, exist_ok=True)

    def save_chat(self, user_id: str, convo_title: str, messages: list):
        safe_title = safe_filename(convo_title)
        filename = os.path.join(self.chat_dir, f"{user_id}_{safe_title}.json")
        chat_data = {
            "user_id": user_id,
            "title": convo_title,
            "messages": messages,
            "last_updated": datetime.utcnow().isoformat()
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, indent=2)

    def load_chat(self, user_id: str, convo_title: str):
        safe_title = safe_filename(convo_title)
        filename = os.path.join(self.chat_dir, f"{user_id}_{safe_title}.json")
        if not os.path.exists(filename):
            return None
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_chats(self, user_id: str):
        if not os.path.exists(self.chat_dir):
            return []
        files = os.listdir(self.chat_dir)
        user_chats = [f for f in files if f.startswith(user_id + "_") and f.endswith(".json")]
        return [f[len(user_id)+1:-5].replace("_", " ") for f in user_chats]

    def generate_intro_and_topics(self, learning_desc: str) -> str:
        prompt = f"""
                    You are a friendly, interactive AI mentor.

                    A learner said: "{learning_desc}"

                    1. Greet warmly.
                    2. Acknowledge the learning goal.
                    3. List 4-6 key subtopics you will teach as bullet points.
                    4. Invite them to start the session with a warm question.

                    Use clear, encouraging language.
"""
        
        
        gemini_api_key = "AIzaSyA5CJMIV4zAxbNDn6jiL4G3Rgl_v5yCBYo"

        llm = LLM(model="gemini/gemini-2.5-flash", provider="google")
        response = llm.call(prompt)
        return response
        

    def generate_role_goal_backstory(self, topic: str):
        role = "Mentor AI Agent"
        goal = f"Help user learn about {topic}."
        backstory = f"You are a mentor AI helping a learner understand {topic} deeply with explanations, questions, and guidance."
        return role, goal, backstory

    def chat_with_agent(self, user_id: str, convo_title: str, user_message: str):
        chat_data = self.load_chat(user_id, convo_title)
        if chat_data is None:
            raise ValueError(f"No chat found for user '{user_id}' with title '{convo_title}'")

        messages = chat_data.get("messages", [])
        messages.append({"role": "user", "content": user_message})

        base_title = convo_title.split(" - ")[0]
        topic = base_title.replace("Learning ", "")

        role, goal, backstory = self.generate_role_goal_backstory(topic)
        mentor_agent = create_mentor_agent(self.llm, role, goal, backstory)

        conversation_text = ""
        for m in messages:
            conversation_text += f"{m['role'].capitalize()}: {m['content']}\n"

        task_prompt = f"Continue this conversation:\n{conversation_text}Mentor:"

        task = Task(
            description="Generate mentor reply",
            agent=mentor_agent,
            function_args={"tool_input": task_prompt},
            expected_output="Text reply continuing the conversation",
            output_key="mentor_reply"
        )

        crew = Crew(agents=[mentor_agent], tasks=[task], verbose=True)
        result = crew.kickoff()
        agent_reply = result.raw.strip()

        messages.append({"role": "mentor", "content": agent_reply})
        self.save_chat(user_id, convo_title, messages)

        return agent_reply, messages

    def launch_mentor_session(
        self,
        user_id: str,
        learning_description: str,
        user_message: Optional[str] = None,
        custom_title: Optional[str] = None
    ):
        title = custom_title if custom_title else f"Learning {learning_description.strip()}"
        chat_data = self.load_chat(user_id, title)

        if chat_data is None:
            messages = []
            intro = self.generate_intro_and_topics(learning_description)
            messages.append({"role": "mentor", "content": intro})
            if user_message:
                messages.append({"role": "user", "content": user_message})
                agent_reply, messages = self.chat_with_agent(user_id, title, user_message)
            self.save_chat(user_id, title, messages)
            return title, messages, intro
        else:
            messages = chat_data.get("messages", [])
            if user_message:
                agent_reply, messages = self.chat_with_agent(user_id, title, user_message)
                return title, messages, agent_reply
            else:
                return title, messages, messages[-1]["content"] if messages else ""
