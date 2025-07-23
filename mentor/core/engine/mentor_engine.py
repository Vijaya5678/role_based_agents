import json
import re
from typing import Optional, Tuple, List

from connection import Connection  # Your existing connection to get LLM


class MentorEngine:
    def __init__(self):
        try:
            conn = Connection()
            self.llm = conn.get_llm()
            if not self.llm:
                raise ValueError("LLM not initialized by Connection. Please check Connection class.")
        except Exception as e:
            print(f"Error initializing LLM in MentorEngine: {e}")
            raise

    def safe_filename(self, title: str) -> str:
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        return safe_title[:50]

    def generate_intro_and_topics(self, context_description: str, extra_instructions: Optional[str] = None) -> Tuple[str, List[str]]:
        instructions_clause = f"{extra_instructions}\n\n" if extra_instructions else ""
        default_behavior = (
            "You are a mentor who is very interactive. "
            "Ask questions, quiz the user, summarize lessons, and check understanding. "
            "Provide a friendly introduction and a list of key topics to learn."
        )

        prompt = f"""
As an interactive AI mentor, create a warm introduction and propose key topics for the learner.
{instructions_clause}
{default_behavior}

Learner context:
{context_description}

Your response MUST be in the following JSON format:
{{
  "introduction": "Your friendly and encouraging introductory message.",
  "topics": [
    "Topic 1: ...",
    "Topic 2: ...",
    "..."
  ]
}}
"""
        try:
            response_text = self.llm.call(prompt)

            cleaned_response_text = response_text.strip()
            if cleaned_response_text.startswith("```json"):
                cleaned_response_text = cleaned_response_text[len("```json"):].strip()
                if cleaned_response_text.endswith("```"):
                    cleaned_response_text = cleaned_response_text[:-len("```")].strip()

            parsed_response = json.loads(cleaned_response_text)
            intro = parsed_response.get("introduction", "Welcome! Let's start learning together.")
            topics = parsed_response.get("topics", ["Introduction", "Key Concepts", "Next Steps"])

            if not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
                topics = ["Introduction", "Key Concepts", "Next Steps"]

            # Clean topics: remove numbering like "Topic 1:" prefix if present
            cleaned_topics = []
            for t in topics:
                cleaned = re.sub(r"^Topic \d+:\s*", "", t, flags=re.I).strip()
                cleaned_topics.append(cleaned)

            return intro, cleaned_topics

        except Exception as e:
            print(f"Error generating intro and topics: {e}")
            fallback_intro = "Hello! I'm your AI mentor, ready to guide you on your journey."
            fallback_topics = ["Introduction", "Core Concepts", "Advanced Topics"]
            return fallback_intro, fallback_topics

    def chat(
        self,
        chat_history: List[dict],
        user_id: str,
        mentor_topics: Optional[List[str]] = None,
        current_topic: Optional[str] = None,
        completed_topics: Optional[List[str]] = None,
    ) -> str:
        """
        Generate mentor reply, enforcing sequential topic learning.
        - chat_history: full conversation so far, latest user message last
        - mentor_topics: full list of mentor topics in order
        - current_topic: the topic currently being taught
        - completed_topics: topics already completed
        """

        if not chat_history:
            return "Hello! How can I assist you today?"

        user_latest_message = chat_history[-1]["content"]

        # Basic validation
        if mentor_topics is None:
            mentor_topics = []
        if completed_topics is None:
            completed_topics = []

        # Default to first topic if current_topic not set
        if current_topic is None and mentor_topics:
            current_topic = mentor_topics[0]

        # Check if user is trying to jump ahead
        def user_mentions_topic(topic: str) -> bool:
            # crude check: topic name substring in message, case insensitive
            return topic.lower() in user_latest_message.lower()

        if mentor_topics and current_topic:
            current_index = mentor_topics.index(current_topic) if current_topic in mentor_topics else -1

            # Check for user mention of any future topic (after current)
            for future_index in range(current_index + 1, len(mentor_topics)):
                future_topic = mentor_topics[future_index]
                if user_mentions_topic(future_topic):
                    # User tries to skip ahead
                    return (
                        f"I see you're curious about **{future_topic}**, but let's make sure we've covered "
                        f"**{current_topic}** first. Would you like me to summarize the current topic or answer questions on it before moving on? "
                        "Or do you want to skip ahead anyway?"
                    )

            # If user mentions a previous topic that is completed, encourage reviewing or moving forward
            for past_index in range(0, current_index):
                past_topic = mentor_topics[past_index]
                if user_mentions_topic(past_topic) and past_topic not in completed_topics:
                    return (
                        f"It looks like you want to revisit **{past_topic}**, which we haven't marked as completed yet. "
                        f"Would you like me to review it with you?"
                    )

        # Build prompt to the LLM to generate focused teaching on current topic

        # Assemble conversation context for LLM prompt
        conversation_text = ""
        for msg in chat_history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                conversation_text += f"User: {content}\n"
            else:
                conversation_text += f"Mentor: {content}\n"

        prompt = f"""
You are an interactive AI mentor focused on teaching the topic: "{current_topic}".

Be engaging, ask questions, quiz the user, summarize lessons, and check understanding.

Conversation so far:
{conversation_text}

Please respond as a friendly mentor, focused only on the current topic "{current_topic}".
"""

        try:
            mentor_reply = self.llm.call(prompt)
            return mentor_reply.strip()
        except Exception as e:
            print(f"Error generating mentor reply: {e}")
            return "Sorry, I encountered a problem generating a response. Could you please try rephrasing?"
