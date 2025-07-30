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

# Adjust system path to find the 'connection' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from connection import Connection

class MentorEngine:
    def __init__(self):
        """Initializes the MentorEngine."""
        self.conn = Connection()
        self.llm_client = self.conn.get_llm()
        self.llm_deployment_name = self.conn.get_llm_deployment_name()
        self.guard = Guard().use_many(
            DetectPII(pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "SSN", "CREDIT_CARD", "IP_ADDRESS"], on_fail="fix")
        )
        self.role_context = self._load_yaml("mentor_roles.yaml")
        self.prompt_templates = self._load_yaml("mentor_prompts.yaml")
        # State to hold summaries for ongoing conversations
        self.conversation_summaries = {}

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Loads a YAML file from the same directory."""
        path = os.path.join(os.path.dirname(__file__), filename)
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _validate_and_sanitize_input(self, input_text: str) -> str:
        return input_text

    def _sanitize_output(self, output_text: str) -> str:
        try:
            if not isinstance(output_text, str):
                return output_text
            validated_output = self.guard.parse(output_text)
            return validated_output.validated_output
        except Exception:
            return output_text

    async def _get_llm_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        temperature: float = 0.7,
        max_tokens: int = 500,
        json_mode: bool = False
    ) -> str:
        """Sends a request to the LLM and returns the sanitized response."""
        completion_params = {
            "model": self.llm_deployment_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            completion_params["response_format"] = {"type": "json_object"}

        response = await self.llm_client.chat.completions.create(**completion_params)
        return self._sanitize_output(response.choices[0].message.content.strip())

    # NEW METHOD: To summarize the conversation history
    async def _get_conversation_summary(self, chat_title: str, chat_history: List[Dict[str, Any]]) -> str:
        """
        Creates and updates a summary of the conversation to keep context size manageable.
        """
        # Define how many messages to keep in the sliding window
        SUMMARY_THRESHOLD = 10 
        
        # Only summarize if the history is long enough
        if len(chat_history) < SUMMARY_THRESHOLD:
            return self.conversation_summaries.get(chat_title, "")

        # Determine which messages need to be summarized
        # We summarize all but the last few messages to keep recent context sharp
        messages_to_summarize = chat_history[:-5]
        
        summary_prompt = (
            "Concisely summarize the key points, user goals, and progress in this conversation. "
            "Focus on information that would be essential for a mentor to remember to continue the conversation effectively."
        )
        
        summary_messages = [{"role": "system", "content": summary_prompt}]
        summary_messages.extend(messages_to_summarize)

        try:
            # Use a smaller max_tokens for the summary itself
            summary = await self._get_llm_completion(summary_messages, temperature=0.3, max_tokens=250)
            self.conversation_summaries[chat_title] = summary
            print(f"Generated new summary for chat '{chat_title}': {summary}")
            return summary
        except Exception as e:
            print(f"Error generating conversation summary: {e}")
            # Return the last known summary if a new one fails
            return self.conversation_summaries.get(chat_title, "")

    async def generate_intro_and_topics(
        self,
        context_description: str,
        extra_instructions: Optional[str] = None,
        role: Optional[str] = None
    ) -> Tuple[str, List[str], List[str]]:
        # This method remains unchanged as it starts a new conversation
        context_description = self._validate_and_sanitize_input(context_description)
        extra_instructions = self._validate_and_sanitize_input(extra_instructions) if extra_instructions else ""
        default_behavior = self.role_context.get("default_instructions", "")
        role_prompt = self.role_context.get("roles", {}).get(role, "")
        prompt_template = self.prompt_templates.get("generate_intro_and_topics", "")
        prompt_content = prompt_template.format(extra_instructions=extra_instructions, default_behavior=default_behavior, role_prompt=role_prompt, context_description=context_description)
        messages = [{"role": "user", "content": prompt_content}]
        try:
            llm_raw_response = await self._get_llm_completion(messages, temperature=0.5, max_tokens=800, json_mode=True)
            parsed = json.loads(llm_raw_response)
            greeting = self._sanitize_output(parsed.get("greeting", "Hello!"))
            topics = [self._sanitize_output(t) for t in parsed.get("topics", [])]
            question = self._sanitize_output(parsed.get("concluding_question", "Shall we start?"))
            suggestions = [self._sanitize_output(s) for s in parsed.get("suggestions", [])]
            return (f"{greeting}\n\nHere are the topics we'll explore:\n- " + "\n- ".join(topics) + f"\n\n{question}", topics, suggestions)
        except Exception as e:
            print(f"Error in generate_intro_and_topics: {e}")
            fallback_intro = "Hello! I'm your mentor, ready to guide you.\n\nHere are some topics:\n- Introduction\n- Core Concepts\n- Advanced Topics\n\nShall we start?"
            return fallback_intro, ["Introduction", "Core Concepts", "Advanced Topics"], ["What should I focus on first?", "Can you explain the first topic?", "How does this relate to my goal?", "Can you quiz me on a topic?"]

    async def chat(
        self,
        chat_history: List[Dict[str, Any]],
        user_id: str,
        chat_title: str, # Added chat_title to manage summaries
        learning_goal: Optional[str],
        skills: List[str],
        difficulty: str,
        role: str,
        mentor_topics: Optional[List[str]] = None,
        current_topic: Optional[str] = None,
        completed_topics: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        """Handles a chat turn using summarization to manage context."""
        if not chat_history:
            return "Please start the conversation with a message.", []

        # MODIFICATION: Get summary and recent messages instead of full history
        summary = await self._get_conversation_summary(chat_title, chat_history)
        
        # Keep the last 6 messages for the "sliding window" of recent context
        recent_history = chat_history[-6:]

        # Build the context for the API call
        system_prompt = self._build_system_context(learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics)
        messages_for_api = [{"role": "system", "content": system_prompt}]
        
        # Add the summary to the context if it exists
        if summary:
            messages_for_api.append({"role": "system", "content": f"Here is a summary of the conversation so far:\n{summary}"})

        # Add the recent history
        messages_for_api.extend(recent_history)

        try:
            # The token limit can now be lower as the context is managed
            llm_raw_response = await self._get_llm_completion(messages_for_api, temperature=0.7, max_tokens=1500, json_mode=True)
            parsed = json.loads(llm_raw_response)
            reply = self._sanitize_output(parsed.get("reply", "I'm sorry, I couldn't form a proper reply."))
            suggestions = [self._sanitize_output(s) for s in parsed.get("suggestions", [])]
            return reply, suggestions
        except json.JSONDecodeError as e:
            print(f"CRITICAL: LLM failed to produce valid JSON even in json_mode. Error: {e}. Response: {llm_raw_response}")
            return "I seem to be having trouble formatting my thoughts. Please try rephrasing your question.", []
        except Exception as e:
            print(f"Error in chat: {e}")
            return "Sorry, I couldn't generate a response at this moment.", []

    def _build_system_context(
        self,
        learning_goal,
        skills,
        difficulty,
        role,
        mentor_topics,
        current_topic,
        completed_topics
    ) -> str:
        # This method remains unchanged
        context_lines = [f"Role: {role}"]
        if learning_goal: context_lines.append(f"Learning Goal: {learning_goal}")
        if skills: context_lines.append(f"Skills: {', '.join(skills)}")
        context_lines.append(f"Difficulty: {difficulty}")
        if mentor_topics: context_lines.append(f"Topics: {', '.join(mentor_topics)}")
        if current_topic: context_lines.append(f"Current Topic: {current_topic}")
        if completed_topics: context_lines.append(f"Completed Topics: {', '.join(completed_topics)}")
        role_instruction = self.role_context["roles"].get(role, "")
        default_instruction = self.role_context.get("default_instructions", "")
        json_output_instruction = (
            "\n\n--- OUTPUT FORMAT ---\n"
            "You MUST provide your response as a single JSON object. This object must contain two keys:\n"
            '1. "reply": (string) Your main conversational response to the user. Use Markdown for formatting.\n'
            '2. "suggestions": (list of strings) A list of 3-4 short, relevant follow-up questions or prompts to guide the user.\n\n'
            "Example:\n"
            '{\n'
            '  "reply": "This is the main answer to the user\'s question.",\n'
            '  "suggestions": ["Tell me more.", "Give me an example.", "What\'s next?"]\n'
            '}'
        )
        return "\n".join(context_lines) + "\n" + role_instruction + "\n" + default_instruction + json_output_instruction
    
    async def generate_topic_prompts(
        self,
        topic: str,
        context_description: str = "",
        role: Optional[str] = None
    ) -> list:
        # This method remains unchanged
        topic = self._validate_and_sanitize_input(topic)
        context_description = self._validate_and_sanitize_input(context_description)
        role_prompt = self.role_context["roles"].get(role, "") if role else ""
        prompt_template = self.prompt_templates.get("generate_topic_prompts", "")
        prompt_content = prompt_template.format(topic=topic, role_prompt=role_prompt, context_description=context_description)
        messages = [{"role": "user", "content": prompt_content}]
        try:
            llm_response = await self._get_llm_completion(messages, temperature=0.5, max_tokens=500, json_mode=True)
            prompts = json.loads(llm_response)
            return [self._sanitize_output(p) for p in prompts]
        except Exception as e:
            print(f"Error in generate_topic_prompts: {e}")
            return [f"What are the basics of {topic}?", f"Give me an example of {topic}", f"How to apply {topic}?", f"Common mistakes in {topic}?"]

