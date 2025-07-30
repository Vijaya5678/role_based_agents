import os
import sys
import re
import json
import yaml
from typing import Optional, Tuple, List, Dict, Any
import guardrails as gd
from guardrails.hub import DetectPII
from guardrails import Guard

from openai.types.chat import ChatCompletionMessageParam

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from connection import Connection

class MentorEngine:
    def __init__(self):
        self.conn = Connection()
        self.llm_client = self.conn.get_llm()
        self.llm_deployment_name = self.conn.get_llm_deployment_name()

        # Initialize Guardrails Guard
        self.guard = Guard().use_many(
            DetectPII(pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "SSN", "CREDIT_CARD", "IP_ADDRESS"], on_fail="fix")
        )

        # Load mentor role context from YAML
        self.role_context = self._load_role_context()

    def _load_role_context(self) -> Dict[str, Any]:
        yaml_path = os.path.join(os.path.dirname(__file__), "mentor_roles.yaml")
        with open(yaml_path, "r") as file:
            return yaml.safe_load(file)

    def safe_filename(self, title: str) -> str:
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        return safe_title[:50]

    def _validate_and_sanitize_input(self, input_text: str) -> str:
        try:
            return input_text
        except Exception:
            return input_text

    def _sanitize_output(self, output_text: str) -> str:
        try:
            validated_output = self.guard.parse(output_text)
            return validated_output.validated_output
        except Exception:
            return output_text

    async def _get_llm_completion(self, messages: List[ChatCompletionMessageParam], temperature: float = 0.7, max_tokens: int = 500) -> str:
        sanitized_messages = []
        for message in messages:
            sanitized_content = self._validate_and_sanitize_input(message["content"])
            sanitized_messages.append({
                "role": message["role"],
                "content": sanitized_content
            })

        response = await self.llm_client.chat.completions.create(
            model=self.llm_deployment_name,
            messages=sanitized_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        raw_output = response.choices[0].message.content.strip()
        sanitized_output = self._sanitize_output(raw_output)
        return sanitized_output

    async def generate_intro_and_topics(self, context_description: str, extra_instructions: Optional[str] = None, role: Optional[str] = None) -> Tuple[str, List[str], List[str]]:
        context_description = self._validate_and_sanitize_input(context_description)
        if extra_instructions:
            extra_instructions = self._validate_and_sanitize_input(extra_instructions)

        instructions_clause = f"{extra_instructions}\n\n" if extra_instructions else ""

        # Fetch default instructions and role prompt from YAML
        default_behavior = self.role_context.get("default_instructions", "")
        role_prompt= self.role_context.get("roles", "")

        prompt_content = f"""
As an interactive AI mentor, provide the following components for a learner's introduction:
1.  A warm, brief, and catchy opening greeting.
2. generate not more than 5 topics keeping in consideration the role details that we are giving you as "roles".
3.  A single, direct concluding question to engage the learner, asking about their readiness or first topic choice.
4.  Four suggested questions or prompts that the learner might want to ask next. These should be relevant to the topics and engaging. Return them as a list of strings.

Do NOT provide any markdown formatting (like bolding, bullet points, or extra descriptions) for the topic titles or suggestions within the JSON output, other than the list structure itself.

{instructions_clause}
{default_behavior}
roles:
{role_prompt}

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
        print("intro",prompt_content)
        messages = [{"role": "user", "content": prompt_content}]
        try:
            llm_raw_response = await self._get_llm_completion(messages, temperature=0.5, max_tokens=800)
            cleaned_response = llm_raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[len("```json"):].strip()
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-len("```")].strip()

            parsed = json.loads(cleaned_response)
            greeting = self._sanitize_output(parsed.get("greeting", "Hello!"))
            topics = [self._sanitize_output(t) for t in parsed.get("topics", [])]
            question = self._sanitize_output(parsed.get("concluding_question", "Shall we start?"))
            suggestions = [self._sanitize_output(s) for s in parsed.get("suggestions", [])]

            return f"{greeting}\n\nHere are the topics we'll explore:\n- " + "\n- ".join(topics) + f"\n\n{question}", topics, suggestions
        except Exception as e:
            print(f"Error in generate_intro_and_topics: {e}")
            fallback_intro = "Hello! I'm your mentor, ready to guide you.\n\nHere are some topics:\n- Introduction\n- Core Concepts\n- Advanced Topics\n\nShall we start?"
            return fallback_intro, ["Introduction", "Core Concepts", "Advanced Topics"], [
                "What should I focus on first?",
                "Can you explain the first topic?",
                "How does this relate to my goal?",
                "Can you quiz me on a topic?"
            ]

    async def generate_topic_prompts(self, topic: str, context_description: str = "", role: Optional[str] = None) -> list:
        topic = self._validate_and_sanitize_input(topic)
        context_description = self._validate_and_sanitize_input(context_description)

        # Fetch role prompt from YAML
        role_prompt = self.role_context["roles"].get(role, "") if role else ""

        prompt_content = f"""
You are an interactive AI mentor. For the topic "{topic}", generate 4 engaging, relevant prompts or questions that a learner might want to ask next. Return ONLY a JSON array of strings, no explanations.
Give short questions not more than 5-6 words each. That should be beginner friendly and easy to understand.
IMPORTANT: Do not include any personally identifiable information in your response.

{role_prompt}

Example:
[
  "What are the basics of {topic}?",
  "Give a real-world example",
  "How do I apply this?",
  "What are common mistakes?"
]

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
            return [self._sanitize_output(p) for p in prompts]
        except Exception as e:
            print(f"Error in generate_topic_prompts: {e}")
            return [
                f"What are the basics of {topic}?",
                f"Give me an example of {topic}",
                f"How to apply {topic}?",
                f"Common mistakes in {topic}?"
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

        sanitized_chat_history = []
        for message in chat_history:
            content = self._validate_and_sanitize_input(message.get("content", ""))
            sanitized_chat_history.append({
                "role": message.get("role", "user"),
                "content": content
            })

        if learning_goal:
            learning_goal = self._validate_and_sanitize_input(learning_goal)
        skills = [self._validate_and_sanitize_input(skill) for skill in skills]
        difficulty = self._validate_and_sanitize_input(difficulty)
        role = self._validate_and_sanitize_input(role)
        mentor_topics = [self._validate_and_sanitize_input(t) for t in mentor_topics or []]
        completed_topics = [self._validate_and_sanitize_input(t) for t in completed_topics or []]

        if not current_topic and mentor_topics:
            current_topic = mentor_topics[0]
        elif current_topic:
            current_topic = self._validate_and_sanitize_input(current_topic)

        messages_for_api = [{"role": "system", "content": self._build_system_context(
            learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics)}]
        messages_for_api.extend(sanitized_chat_history)

        try:
            reply = await self._get_llm_completion(messages_for_api, temperature=0.7, max_tokens=500)
            return reply
        except Exception as e:
            print(f"Error in chat: {e}")
            return "Sorry, I couldn't generate a response at this moment."

    def _build_system_context(self, learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics) -> str:
        context_lines = []
        context_lines.append(f"Role: {role}")
        if learning_goal:
            context_lines.append(f"Learning Goal: {learning_goal}")
        if skills:
            context_lines.append(f"Skills: {', '.join(skills)}")
        context_lines.append(f"Difficulty: {difficulty}")
        if mentor_topics:
            context_lines.append(f"Topics: {', '.join(mentor_topics)}")
        if current_topic:
            context_lines.append(f"Current Topic: {current_topic}")
        if completed_topics:
            context_lines.append(f"Completed Topics: {', '.join(completed_topics)}")

        role_instruction = self.role_context["roles"].get(role, "")
        default_instruction = self.role_context.get("default_instructions", "")

        return "\n".join(context_lines) + "\n" + role_instruction + "\n" + default_instruction
