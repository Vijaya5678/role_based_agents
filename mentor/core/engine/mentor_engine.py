# mentor/core/engine/mentor_engine.py

import json
import re
import os
import sys
import traceback # Added for detailed error reporting
from typing import Optional, Tuple, List, Dict, Any
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# FIX: Changed to relative import for Connection.py
from connection import Connection
# Import necessary types for OpenAI messages
from openai.types.chat import ChatCompletionMessageParam

class MentorEngine:
    def __init__(self):
        try:
            self.conn = Connection()
            # FIX: Get both the client and the deployment name from Connection
            self.llm_client = self.conn.get_llm() # This returns AsyncAzureOpenAI client
            self.llm_deployment_name = self.conn.get_llm_deployment_name() # This returns your deployment string

            if not self.llm_client:
                raise ValueError("LLM client not initialized by Connection. Please check Connection class.")
        except Exception as e:
            print(f"Error initializing LLM in MentorEngine: {e}")
            traceback.print_exc()
            raise

    def safe_filename(self, title: str) -> str:
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        return safe_title[:50]

    async def _get_llm_completion(self, messages: List[ChatCompletionMessageParam], temperature: float = 0.7, max_tokens: int = 500) -> str:
        """
        Helper method to interact with the LLM via the AsyncAzureOpenAI client.
        """
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.llm_deployment_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Error during LLM completion request: {e}")
            traceback.print_exc()
            raise # Re-raise to allow calling functions to handle

    async def generate_intro_and_topics(self, context_description: str, extra_instructions: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Generates an introductory message and a list of topics using the LLM.
        FIX: Made this function async.
        """
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

Do NOT provide any markdown formatting (like bolding, bullet points, or extra descriptions) for the topic titles within the JSON output, other than the list structure itself.

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
  "concluding_question": "Your single, direct concluding question."
}}
Ensure 'topics' contains only the exact topic titles as strings.
"""
        messages: List[ChatCompletionMessageParam] = [
            {"role": "user", "content": prompt_content}
        ]

        llm_raw_response = "" # Initialize for debugging in case of error
        try:
            # FIX: Call the async helper method to get LLM response
            llm_raw_response = await self._get_llm_completion(messages, temperature=0.5, max_tokens=700)

            # Clean potential markdown code block wrappers
            cleaned_response_text = llm_raw_response.strip()
            if cleaned_response_text.startswith("```json"):
                cleaned_response_text = cleaned_response_text[len("```json"):].strip()
                if cleaned_response_text.endswith("```"):
                    cleaned_response_text = cleaned_response_text[:-len("```")].strip()

            parsed_response = json.loads(cleaned_response_text)

            greeting = parsed_response.get("greeting", "Hello there!")
            topics_for_internal_use = parsed_response.get("topics", ["Introduction", "Key Concepts", "Next Steps"])
            concluding_question = parsed_response.get("concluding_question", "Ready to begin?")

            if not isinstance(topics_for_internal_use, list) or not all(isinstance(t, str) for t in topics_for_internal_use):
                print("Warning: LLM returned topics in an unexpected format. Using fallback topics.")
                topics_for_internal_use = ["Introduction", "Key Concepts", "Next Steps"]

            # Construct the final full message that will be sent to the frontend
            topics_formatted_list = "\n- " + "\n- ".join(topics_for_internal_use)
            intro_and_topics_message = (
                f"{greeting}\n\n"
                f"Here are the topics we'll explore:\n{topics_formatted_list}\n\n"
                f"{concluding_question}"
            )

            return intro_and_topics_message, topics_for_internal_use

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error in generate_intro_and_topics: {e}. Raw response: {llm_raw_response}")
            traceback.print_exc()
            fallback_intro_message = (
                "Hello! I'm your AI mentor, ready to guide you on your journey.\n\n"
                "Here are some topics we can explore:\n"
                "- Introduction\n"
                "- Core Concepts\n"
                "- Advanced Topics\n\n"
                "Ready to begin?"
            )
            fallback_topics_list = ["Introduction", "Core Concepts", "Advanced Topics"]
            return fallback_intro_message, fallback_topics_list
        except Exception as e:
            print(f"❌ Error generating intro and topics: {e}")
            traceback.print_exc()
            fallback_intro_message = (
                "Hello! I'm your AI mentor, but I'm having a little trouble at the moment. Please try again.\n\n"
                "Here are some generic topics:\n"
                "- Introduction\n"
                "- Core Concepts\n"
                "- Advanced Topics\n\n"
                "Ready to begin?"
            )
            fallback_topics_list = ["Introduction", "Core Concepts", "Advanced Topics"]
            return fallback_intro_message, fallback_topics_list

    # FIX: Added missing parameters and made the function async
    async def chat(
        self,
        chat_history: List[Dict[str, Any]], # Use Dict[str, Any] as ChatMessage objects are converted to dicts
        user_id: str,
        learning_goal: Optional[str],
        skills: List[str],
        difficulty: str,
        role: str,
        mentor_topics: Optional[List[str]] = None,
        current_topic: Optional[str] = None,
        completed_topics: Optional[List[str]] = None,
    ) -> str:
        """
        Generate mentor reply, enforcing sequential topic learning.
        - chat_history: full conversation so far, latest user message last
        - learning_goal: User's overall learning objective
        - skills: User's existing skills/interests
        - difficulty: User's preferred learning difficulty
        - role: User's role (e.g., "student")
        - mentor_topics: full list of mentor topics in order
        - current_topic: the topic currently being taught
        - completed_topics: topics already completed
        """

        if not chat_history:
            return "Hello! How can I assist you today?"

        user_latest_message = chat_history[-1]["content"]

        # Basic validation and defaulting
        if mentor_topics is None:
            mentor_topics = []
        if completed_topics is None:
            completed_topics = []

        # Default to first topic if current_topic not set and topics exist
        if current_topic is None and mentor_topics:
            current_topic = mentor_topics[0]

        # Logic to check if user is trying to jump ahead or revisit past topics
        def user_mentions_topic(topic: str) -> bool:
            return topic.lower() in user_latest_message.lower()

        if mentor_topics and current_topic:
            try:
                current_index = mentor_topics.index(current_topic)
                # Check for user mention of any future topic (after current)
                for future_index in range(current_index + 1, len(mentor_topics)):
                    future_topic = mentor_topics[future_index]
                    if user_mentions_topic(future_topic):
                        return (
                            f"I see you're curious about **{future_topic}**, but let's make sure we've covered "
                            f"**{current_topic}** first. Would you like me to summarize the current topic or answer questions on it before moving on? "
                            f"Or do you want to skip ahead anyway?"
                        )

                # If user mentions a previous topic that is completed, encourage reviewing or moving forward
                for past_index in range(0, current_index):
                    past_topic = mentor_topics[past_index]
                    if user_mentions_topic(past_topic) and past_topic not in completed_topics:
                        # You might adjust this logic: if it's not completed, maybe it was skipped.
                        # For now, this implies you're reminding them to complete it.
                        return (
                            f"It looks like you want to revisit **{past_topic}**, which we were working on earlier. "
                            f"Would you like me to review it with you before we continue with **{current_topic}**?"
                        )
            except ValueError: # current_topic not found in mentor_topics
                print(f"Warning: current_topic '{current_topic}' not found in mentor_topics.")
                pass # Continue to general chat if topic not found in ordered list


        # Build system message for the LLM
        system_context = self._build_system_context(
            learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics
        )

        # Convert chat_history into the format required by OpenAI API
        # Ensure 'timestamp' and 'audio_url' are not passed to the LLM directly as they are custom
        messages_for_api: List[ChatCompletionMessageParam] = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in chat_history if "role" in msg and "content" in msg
        ]

        if system_context:
            messages_for_api.insert(0, {"role": "system", "content": system_context})

        try:
            # FIX: Call the async helper method to get LLM response
            mentor_reply = await self._get_llm_completion(messages_for_api)
            return mentor_reply.strip()
        except Exception as e:
            print(f"❌ Error generating mentor reply in chat method: {e}")
            traceback.print_exc()
            return "Sorry, I encountered a problem generating a response. Could you please try rephrasing?"

    def _build_system_context(self, learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics) -> str:
        """
        Builds the system context string for the LLM based on session parameters.
        """
        context_parts = [
            "You are an AI mentor, highly interactive, supportive, and knowledgeable.",
            "Your goal is to guide the user through their learning journey by asking questions, explaining concepts, summarizing lessons, and checking understanding.",
            "Always maintain a positive and encouraging tone.",
            f"The user's role is: {role}.",
            f"Their preferred learning difficulty is: {difficulty}.",
            f"Their general skills/interests are: {', '.join(skills)}."
        ]
        if learning_goal:
            context_parts.append(f"Their specific learning goal for this session is: {learning_goal}.")
        if mentor_topics:
            context_parts.append(f"The overall topics planned for this session are: {', '.join(mentor_topics)}.")
        if current_topic:
            context_parts.append(f"We are currently focusing on the topic: '{current_topic}'.")
        if completed_topics:
            context_parts.append(f"Topics already covered: {', '.join(completed_topics)}.")

        return "\n".join(context_parts)