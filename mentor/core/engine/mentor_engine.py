import os
import sys
import re
import json
from typing import Optional, Tuple, List, Dict, Any
import guardrails as gd
from guardrails.hub import DetectPII
#, ExcludeSqlInjection, ToxicLanguage
from guardrails import Guard

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from connection import Connection
from openai.types.chat import ChatCompletionMessageParam

class MentorEngine:
    def __init__(self):
        self.conn = Connection()
        self.llm_client = self.conn.get_llm()
        self.llm_deployment_name = self.conn.get_llm_deployment_name()
        
        # Initialize Guardrails Guard with PII detection and other safety measures
        self.guard = Guard().use_many(
            DetectPII(pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "SSN", "CREDIT_CARD", "IP_ADDRESS"], on_fail="fix"),
            #ExcludeSqlInjection(on_fail="exception"),
            #ToxicLanguage(threshold=0.8, on_fail="fix")
        )
        
    def safe_filename(self, title: str) -> str:
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        return safe_title[:50]

    def _validate_and_sanitize_input(self, input_text: str) -> str:
        """
        Validate and sanitize user input to prevent PII from being processed
        """
        try:
            # Use stricter input guard to block PII in user input
            validated_input = self.input_guard.parse(input_text)
            return validated_input.validated_output
        except Exception as e:
            return input_text


    def _sanitize_output(self, output_text: str) -> str:
        """
        Sanitize LLM output to ensure no PII leaks through
        """
        try:
            # Use the guard to sanitize output
            validated_output = self.guard.parse(output_text)
            return validated_output.validated_output
        except Exception as e:
            return output_text

    async def _get_llm_completion(self, messages: List[ChatCompletionMessageParam], temperature: float = 0.7, max_tokens: int = 500) -> str:
        # Sanitize input messages before sending to LLM
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
        
        # Sanitize the output before returning
        sanitized_output = self._sanitize_output(raw_output)
        return sanitized_output

    async def generate_intro_and_topics(self, context_description: str, extra_instructions: Optional[str] = None) -> Tuple[str, List[str], List[str]]:
        # Sanitize input parameters
        context_description = self._validate_and_sanitize_input(context_description)
        if extra_instructions:
            extra_instructions = self._validate_and_sanitize_input(extra_instructions)
        
        instructions_clause = f"{extra_instructions}\n\n" if extra_instructions else ""
        default_behavior = (
            "You are a mentor who is very interactive. "
            "Ask questions, quiz the user, summarize lessons, and check understanding. "
            "IMPORTANT: Never include any personally identifiable information (PII) such as names, email addresses, phone numbers, or addresses in your responses."
        )

        prompt_content = f"""
As an interactive AI mentor, provide the following components for a learner's introduction:
1.  A warm, brief, and catchy opening greeting.
2.  A list of key topic titles for the learning journey. These should be concise and relevant. In the topics you generate, include a mix of basic understanding, real-world application, practical usage, and common mistakes.It shoudl have end to end what all you required someone to learn for that skill. Like examples,use cases, etc
3.  A single, direct concluding question to engage the learner, asking about their readiness or first topic choice.
4.  Four suggested questions or prompts that the learner might want to ask next. These should be relevant to the topics and engaging. Return them as a list of strings.

Do NOT provide any markdown formatting (like bolding, bullet points, or extra descriptions) for the topic titles or suggestions within the JSON output, other than the list structure itself.
IMPORTANT: Do not include any personally identifiable information in your response.

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

            # Additional sanitization of parsed content
            greeting = self._sanitize_output(greeting)
            concluding_question = self._sanitize_output(concluding_question)
            topics_for_internal_use = [self._sanitize_output(topic) for topic in topics_for_internal_use]
            suggestions = [self._sanitize_output(suggestion) for suggestion in suggestions]

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
            print(f"Error in generate_intro_and_topics: {e}")
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
        # Sanitize inputs
        topic = self._validate_and_sanitize_input(topic)
        context_description = self._validate_and_sanitize_input(context_description)
        
        prompt_content = f"""
You are an interactive AI mentor. For the topic "{topic}", generate 4 engaging, relevant prompts or questions that a learner might want to ask next. Return ONLY a JSON array of strings, no explanations.
Give short questions not more than 5-6 words each. That should be beginner friendly and easy to understand.
IMPORTANT: Do not include any personally identifiable information in your response.

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
            
            # Sanitize each prompt
            if isinstance(prompts, list) and len(prompts) == 4:
                sanitized_prompts = [self._sanitize_output(prompt) for prompt in prompts]
                return sanitized_prompts
            else:
                return [
                    f"What are the basics of {topic}?",
                    f"Can you give me a real-world example of {topic}?",
                    f"How do I apply {topic} in practice?",
                    f"What are common mistakes in {topic}?"
                ]
        except Exception as e:
            print(f"Error in generate_topic_prompts: {e}")
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

        # Sanitize chat history
        sanitized_chat_history = []
        for message in chat_history:
            if "content" in message:
                sanitized_content = self._validate_and_sanitize_input(message["content"])
                sanitized_message = message.copy()
                sanitized_message["content"] = sanitized_content
                sanitized_chat_history.append(sanitized_message)
            else:
                sanitized_chat_history.append(message)

        user_latest_message = sanitized_chat_history[-1]["content"]

        # Sanitize other inputs
        if learning_goal:
            learning_goal = self._validate_and_sanitize_input(learning_goal)
        skills = [self._validate_and_sanitize_input(skill) for skill in skills]
        difficulty = self._validate_and_sanitize_input(difficulty)
        role = self._validate_and_sanitize_input(role)

        if mentor_topics is None:
            mentor_topics = []
        else:
            mentor_topics = [self._validate_and_sanitize_input(topic) for topic in mentor_topics]
            
        if completed_topics is None:
            completed_topics = []
        else:
            completed_topics = [self._validate_and_sanitize_input(topic) for topic in completed_topics]

        if current_topic:
            current_topic = self._validate_and_sanitize_input(current_topic)
        elif mentor_topics:
            current_topic = mentor_topics[0]

        def user_mentions_topic(topic: str) -> bool:
            return topic.lower() in user_latest_message.lower()

        system_context = self._build_system_context(
            learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics
        )

        messages_for_api: List[ChatCompletionMessageParam] = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in sanitized_chat_history if "role" in msg and "content" in msg
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
            "IMPORTANT: Never include any personally identifiable information (PII) in your responses, including but not limited to names, email addresses, phone numbers, social security numbers, addresses, or IP addresses.\n"
            "if your role is 'Techno Functional' then user is not that technical, he is tech-functional , looking for a mentor who can guide them in both technical and functional aspects of their learning journey. "
            "If your role is 'Executive' then user is executive and is looking for a mentor who can guide them in executive level,teach them keeping their grade in mind "
            "If your role is 'Technical' then user is very technical and looking for a mentor who can guide them in technical aspects of their learning journey. "
            "in your intro say that for executuve like you or technical person like you, mention the role/persona user gave"
            "You are a mentor who is very interactive and strict to particular domain that the user is interested in. "
            "If someone asked something which is not related to that domain. redirect them to that topic mentor. "
            "Tell the user to open a new session with that topic mentor."
            "Ask questions, quiz the user, "
            "summarize lessons, and check understanding. "
            "Guide the user through topics sequentially unless they ask to revisit or skip."
        )
        return context