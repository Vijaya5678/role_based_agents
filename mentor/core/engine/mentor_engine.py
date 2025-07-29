import os
import sys
import re
import json
from typing import Optional, Tuple, List, Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from connection import Connection
from openai.types.chat import ChatCompletionMessageParam

class MentorEngine:
    def __init__(self):
        self.conn = Connection()
        self.llm_client = self.conn.get_llm()
        self.llm_deployment_name = self.conn.get_llm_deployment_name()

    def safe_filename(self, title: str) -> str:
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        return safe_title[:50]

    async def _get_llm_completion(self, messages: List[ChatCompletionMessageParam], temperature: float = 0.7, max_tokens: int = 500) -> str:
        response = await self.llm_client.chat.completions.create(
            model=self.llm_deployment_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()

    async def generate_intro_and_topics(self, context_description: str, extra_instructions: Optional[str] = None) -> Tuple[str, List[str], List[str]]:
        instructions_clause = f"{extra_instructions}\n\n" if extra_instructions else ""
        default_behavior = (
            "You are a mentor who is very interactive. "
            "Ask questions, quiz the user, summarize lessons, and check understanding. "
        )

        prompt_content = f"""
As an interactive AI mentor, provide the following components for a learner's introduction:
1.  A warm, brief, and catchy opening greeting.
2.  A list of key topic titles for the learning journey. These should be concise and relevant.
3.  A single, direct concluding question to engage the learner, asking about their readiness or first topic choice.
4.  Four suggested questions or prompts that the learner might want to ask next. These should be relevant to the topics and engaging. Return them as a list of strings.

Do NOT provide any markdown formatting (like bolding, bullet points, or extra descriptions) for the topic titles or suggestions within the JSON output, other than the list structure itself.

{instructions_clause}
{default_behavior}

Learner context:
{context_description}

Your response MUST be in the following JSON format:
{{
  "greeting": "Your friendly and encouraging short introductory message.",
  "topics": [
    "Topic 1 Title",
    "Topic 2 Title",
    "..."
  ],
  "concluding_question": "Your single, direct concluding question.",
  "suggestions": [
    "Suggestion 1",
    "Suggestion 2",
    "Suggestion 3",
    "Suggestion 4"
  ]
}}
Ensure 'topics' and 'suggestions' contain only the exact strings.
"""
        messages: List[ChatCompletionMessageParam] = [
            {"role": "user", "content": prompt_content}
        ]

        try:
            llm_raw_response = await self._get_llm_completion(messages, temperature=0.5, max_tokens=800)
            cleaned_response_text = llm_raw_response.strip()
            if cleaned_response_text.startswith("```json"):
                cleaned_response_text = cleaned_response_text[len("```json"):].strip()
                if cleaned_response_text.endswith("```"):
                    cleaned_response_text = cleaned_response_text[:-len("```")].strip()

            parsed_response = json.loads(cleaned_response_text)

            greeting = parsed_response.get("greeting", "Hello there!")
            topics_for_internal_use = parsed_response.get("topics", ["Introduction", "Key Concepts", "Next Steps"])
            concluding_question = parsed_response.get("concluding_question", "Ready to begin?")
            suggestions = parsed_response.get("suggestions", [
                "Can you explain the first topic?",
                "What should I focus on first?",
                "How does this relate to my goal?",
                "Can you quiz me on a topic?"
            ])

            if not isinstance(topics_for_internal_use, list) or not all(isinstance(t, str) for t in topics_for_internal_use):
                topics_for_internal_use = ["Introduction", "Key Concepts", "Next Steps"]

            if not isinstance(suggestions, list) or len(suggestions) < 4:
                suggestions = [
                    "Can you explain the first topic?",
                    "What should I focus on first?",
                    "How does this relate to my goal?",
                    "Can you quiz me on a topic?"
                ]

            topics_formatted_list = "\n- " + "\n- ".join(topics_for_internal_use)
            intro_and_topics_message = (
                f"{greeting}\n\n"
                f"Here are the topics we'll explore:\n{topics_formatted_list}\n\n"
                f"{concluding_question}"
            )

            return intro_and_topics_message, topics_for_internal_use, suggestions

        except Exception as e:
            fallback_intro_message = (
                "Hello! I'm your AI mentor, ready to guide you on your journey.\n\n"
                "Here are some topics we can explore:\n"
                "- Introduction\n"
                "- Core Concepts\n"
                "- Advanced Topics\n\n"
                "Ready to begin?"
            )
            fallback_topics_list = ["Introduction", "Core Concepts", "Advanced Topics"]
            fallback_suggestions = [
                "Can you explain the first topic?",
                "What should I focus on first?",
                "How does this relate to my goal?",
                "Can you quiz me on a topic?"
            ]
            return fallback_intro_message, fallback_topics_list, fallback_suggestions

    async def generate_topic_prompts(self, topic: str, context_description: str = "") -> list:
        """
        Given a topic, generate 4 engaging prompts/questions for the user.
        """
        prompt_content = f"""
You are an interactive AI mentor. For the topic "{topic}", generate 4 engaging, relevant prompts or questions that a learner might want to ask next. Return ONLY a JSON array of strings, no explanations.
Give short questions not more than 5-6 words each. That should be beginner friendly and easy to understand.
Example:
[
  "What are the basics of {topic}?",
  "give me a real-world example of {topic}?",
  "How do I apply {topic} in practice?",
  "What are common mistakes in {topic}?"
]

Give short questions not more than 5-6 words each.
Learner context: {context_description}
"""
        messages = [{"role": "user", "content": prompt_content}]
        try:
            llm_response = await self._get_llm_completion(messages, temperature=0.5, max_tokens=300)
            cleaned = llm_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[len("```json"):].strip()
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-len("```")].strip()
            prompts = json.loads(cleaned)
            if isinstance(prompts, list) and len(prompts) == 4:
                return prompts
            else:
                return [
                    f"What are the basics of {topic}?",
                    f"Can you give me a real-world example of {topic}?",
                    f"How do I apply {topic} in practice?",
                    f"What are common mistakes in {topic}?"
                ]
        except Exception as e:
            return [
                f"What are the basics of {topic}?",
                f"Can you give me a real-world example of {topic}?",
                f"How do I apply {topic} in practice?",
                f"What are common mistakes in {topic}?"
            ]

    async def chat(
        self,
        chat_history: List[Dict[str, Any]],
        user_id: str,
        learning_goal: Optional[str],
        skills: List[str],
        difficulty: str,
        role: str,
        mentor_topics: Optional[List[str]] = None,
        current_topic: Optional[str] = None,
        completed_topics: Optional[List[str]] = None,
    ) -> str:
        if not chat_history:
            return "Please start the conversation with a message."

        user_latest_message = chat_history[-1]["content"]

        if mentor_topics is None:
            mentor_topics = []
        if completed_topics is None:
            completed_topics = []

        if current_topic is None and mentor_topics:
            current_topic = mentor_topics[0]

        def user_mentions_topic(topic: str) -> bool:
            return topic.lower() in user_latest_message.lower()

        system_context = self._build_system_context(
            learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics
        )

        messages_for_api: List[ChatCompletionMessageParam] = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in chat_history if "role" in msg and "content" in msg
        ]

        messages_for_api.insert(0, {"role": "system", "content": system_context})

        try:
            reply = await self._get_llm_completion(messages_for_api, temperature=0.7, max_tokens=500)
            return reply
        except Exception as e:
            print(f"Error in chat: {e}")
            return "Sorry, I couldn't generate a response at this moment."

    def _build_system_context(self, learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics) -> str:
        context = f"Role: {role}\n"
        if learning_goal:
            context += f"Learning Goal: {learning_goal}\n"
        if skills:
            context += f"Skills: {', '.join(skills)}\n"
        context += f"Difficulty: {difficulty}\n"
        if mentor_topics:
            context += f"Topics: {', '.join(mentor_topics)}\n"
        if current_topic:
            context += f"Current Topic: {current_topic}\n"
        if completed_topics:
            context += f"Completed Topics: {', '.join(completed_topics)}\n"
        context += (
            "You are a mentor who is very interactive and strict to particular domain that the user is interested in. "
            "If someone asked something which is not related to that domain. redirect them to that topic mentor. "
            "Tell the user to open a new session with that topic mentor."
            "Ask questions, quiz the user, "
            "summarize lessons, and check understanding. "
            "Guide the user through topics sequentially unless they ask to revisit or skip."
        )
        return context