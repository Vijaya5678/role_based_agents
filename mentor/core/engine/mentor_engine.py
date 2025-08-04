import os
import sys
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
        # Load all prompts from a single configuration file
        self.prompts = self._load_yaml("prompts.yaml")
        # State to hold summaries for ongoing conversations
        self.conversation_summaries = {}

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Loads a YAML file from the same directory."""
        path = os.path.join(os.path.dirname(__file__), filename)
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _validate_and_sanitize_input(self, input_text: str) -> str:
        # Placeholder for future input validation logic
        return input_text

    def _sanitize_output(self, output_text: str) -> str:
        """Sanitizes output to remove PII using Guardrails."""
        try:
            if not isinstance(output_text, str):
                return output_text
            validated_output = self.guard.parse(output_text)
            return validated_output.validated_output
        except Exception:
            # If sanitization fails, return the original text to avoid breaking the flow
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

    async def _get_conversation_summary(self, chat_title: str, chat_history: List[Dict[str, Any]]) -> str:
        """Creates and updates a summary of the conversation to keep context size manageable."""
        SUMMARY_THRESHOLD = 10
        if len(chat_history) < SUMMARY_THRESHOLD:
            return self.conversation_summaries.get(chat_title, "")

        messages_to_summarize = chat_history[:-5]
        summary_prompt = self.prompts["tasks"]["summarize_conversation"]
        
        summary_messages = [{"role": "system", "content": summary_prompt}]
        summary_messages.extend(messages_to_summarize)

        try:
            summary = await self._get_llm_completion(summary_messages, temperature=0.3, max_tokens=250)
            self.conversation_summaries[chat_title] = summary
            print(f"Generated new summary for chat '{chat_title}': {summary}")
            return summary
        except Exception as e:
            print(f"Error generating conversation summary: {e}")
            return self.conversation_summaries.get(chat_title, "")

    async def generate_intro_and_topics(
        self,
        context_description: str,
        extra_instructions: Optional[str] = None,
        role: Optional[str] = None,
        skills: Optional[List[str]] = None
    ) -> Tuple[str, List[str], List[str]]:
        context_description = self._validate_and_sanitize_input(context_description)
        extra_instructions = self._validate_and_sanitize_input(extra_instructions) if extra_instructions else ""
        
        default_behavior = self.prompts["default_instructions"]
        role_prompt = self.prompts["roles"].get(role, self.prompts["roles"]["default"])
        prompt_template = self.prompts["tasks"]["generate_intro_and_topics"]

        skills_based_suggestions = []
        if skills:
            skills_str = ", ".join(skills)
            skills_based_suggestions = [
                f"Can you explain {skills_str}?",
                f"What are the key concepts of {skills_str}?",
                f"Can you give me a real-world example of {skills_str}?"
            ]

        prompt_content = prompt_template.format(
            extra_instructions=extra_instructions,
            default_behavior=default_behavior,
            role_prompt=role_prompt,
            context_description=context_description,
            skills_suggestions=json.dumps(skills_based_suggestions)
        )
        messages = [{"role": "user", "content": prompt_content}]
        
        try:
            llm_raw_response = await self._get_llm_completion(messages, temperature=0.5, max_tokens=800, json_mode=True)
            parsed = json.loads(llm_raw_response)
            greeting = self._sanitize_output(parsed.get("greeting", "Hello!"))
            topics = [self._sanitize_output(t) for t in parsed.get("topics", [])]
            question = self._sanitize_output(parsed.get("concluding_question", "Shall we start?"))
            
            suggestions = skills_based_suggestions or [self._sanitize_output(s) for s in parsed.get("suggestions", [])]
            
            intro_message = f"{greeting}\n\nHere are the topics we'll explore:\n- " + "\n- ".join(topics) + f"\n\n{question}"
            return (intro_message, topics, suggestions)
        except Exception as e:
            print(f"Error in generate_intro_and_topics: {e}")
            fallback_intro = "Hello! I'm your mentor, ready to guide you.\n\nHere are some topics:\n- Introduction\n- Core Concepts\n- Advanced Topics\n\nShall we start?"
            fallback_suggestions = skills_based_suggestions or ["Explain the first topic.", "How does this relate to my goal?"]
            return fallback_intro, ["Introduction", "Core Concepts", "Advanced Topics"], fallback_suggestions

    async def _serve_next_quiz_question(self, quiz_state: dict) -> Tuple[str, List[str], dict]:
        """Formats and returns the next quiz question or ends the quiz."""
        next_q_num = quiz_state.get("current_question", 1)

        if next_q_num > quiz_state["total_questions"]:
            quiz_state["is_active"] = False
            score = quiz_state["score"]
            total = quiz_state["total_questions"]
            percentage = (score / total) * 100 if total > 0 else 0
            reply = (
                f"🎉 **Quiz Complete!**\n\n"
                f"You scored {score}/{total} ({percentage:.0f}%).\n\n"
                "You can now continue exploring this topic or move to the next one."
            )
            suggestions = ["Summarize this topic", "Move to the next topic", "Explain the concepts I got wrong"]
            return reply, suggestions, quiz_state

        next_question_data = quiz_state["questions"][next_q_num - 1]
        question_text = next_question_data.get("question")
        options = next_question_data.get("options", {})
        
        reply = f"**Question {next_q_num}/{quiz_state['total_questions']}**\n{question_text}"
        
        suggestions = [
            f"A) {options.get('A', 'Option A')}",
            f"B) {options.get('B', 'Option B')}",
            f"C) {options.get('C', 'Option C')}",
            f"D) {options.get('D', 'Option D')}"
        ]
        
        print(f"ENGINE: Serving Q{next_q_num}. State: {quiz_state}")
        return reply, suggestions, quiz_state

    async def chat(
        self,
        chat_history: List[Dict[str, Any]],
        user_id: str,
        chat_title: str,
        learning_goal: Optional[str],
        skills: List[str],
        difficulty: str,
        role: str,
        mentor_topics: Optional[List[str]] = None,
        current_topic: Optional[str] = None,
        completed_topics: Optional[List[str]] = None,
        is_quiz_mode: bool = False,
        quiz_state: Optional[dict] = None,
    ) -> Tuple[str, List[str], Optional[dict]]:
        if not chat_history:
            return "Please start the conversation with a message.", [], None

        last_user_message = chat_history[-1]['content'].strip()
        
        if is_quiz_mode and quiz_state and quiz_state.get("is_active") and last_user_message == "Next Question":
            print("ENGINE: User requested next question.")
            return await self._serve_next_quiz_question(quiz_state)

        summary = await self._get_conversation_summary(chat_title, chat_history)
        recent_history = chat_history[-6:]

        system_prompt = self._build_system_context(learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics)
        messages_for_api = [{"role": "system", "content": system_prompt}]

        if summary:
            user_prompt_wrapper = self.prompts["tasks"]["chat"]["user_prompt_wrapper"]
            messages_for_api.append({"role": "system", "content": user_prompt_wrapper.format(summary=summary)})

        messages_for_api.extend(recent_history)

        try:
            llm_raw_response = await self._get_llm_completion(messages_for_api, temperature=0.7, max_tokens=1500, json_mode=True)
            parsed = json.loads(llm_raw_response)
            reply = self._sanitize_output(parsed.get("reply", "I'm sorry, I couldn't form a proper reply."))
            suggestions = [self._sanitize_output(s) for s in parsed.get("suggestions", [])]

            user_message_count = len([msg for msg in chat_history if msg.get("role") == "user"])
            if user_message_count >= 5 and not is_quiz_mode:
                if not any("quiz" in s.lower() for s in suggestions):
                    suggestions.append("Quiz me!")

            return reply, suggestions, quiz_state
        except json.JSONDecodeError as e:
            print(f"CRITICAL: LLM failed to produce valid JSON. Error: {e}. Response: {llm_raw_response}")
            return "I seem to be having trouble formatting my thoughts. Please try rephrasing your question.", [], quiz_state
        except Exception as e:
            print(f"Error in chat: {e}")
            return "I'm sorry, I couldn't understand your question. Could you please rephrase it?", [], quiz_state

    def _build_system_context(
        self, learning_goal, skills, difficulty, role, mentor_topics, current_topic, completed_topics
    ) -> str:
        context_lines = [f"Role: {role}"]
        if learning_goal: context_lines.append(f"Learning Goal: {learning_goal}")
        if skills: context_lines.append(f"Skills: {', '.join(skills)}")
        context_lines.append(f"Difficulty: {difficulty}")
        if mentor_topics: context_lines.append(f"Topics: {', '.join(mentor_topics)}")
        if current_topic: context_lines.append(f"Current Topic: {current_topic}")
        if completed_topics: context_lines.append(f"Completed Topics: {', '.join(completed_topics)}")
        
        role_instruction = self.prompts["roles"].get(role, self.prompts["roles"]["default"])
        default_instruction = self.prompts["default_instructions"]
        json_output_instruction = self.prompts["shared_components"]["json_output_format"]
        system_prompt_template = self.prompts["tasks"]["chat"]["system_prompt"]

        return system_prompt_template.format(
            context_summary="\n".join(context_lines),
            role_instruction=role_instruction,
            default_instruction=default_instruction,
            json_output_instruction=json_output_instruction
        )
    
    async def start_quiz(
        self,
        chat_history: List[Dict[str, Any]],
        user_id: str,
        chat_title: str,
        learning_goal: Optional[str],
        skills: List[str],
        difficulty: str,
        role: str,
        mentor_topics: Optional[List[str]] = None,
    ) -> Tuple[str, List[str], dict]:
        """Starts a quiz and returns ONLY the first question."""
        print("ENGINE: Starting quiz...")
        summary = await self._get_conversation_summary(chat_title, chat_history)
        system_prompt = self._build_quiz_context(learning_goal, skills, difficulty, role, mentor_topics)
        
        quiz_prompt = self.prompts["tasks"]["start_quiz"]
        messages_for_api = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": quiz_prompt.format(
                conversation_summary=summary,
                chat_history=str(chat_history[-10:])
            )}
        ]
        
        try:
            llm_raw_response = await self._get_llm_completion(messages_for_api, temperature=0.7, max_tokens=1500, json_mode=True)
            parsed = json.loads(llm_raw_response)
            
            questions = parsed.get("questions", [])
            if not questions:
                return "I couldn't generate a quiz right now. Let's try again later.", [], {}

            quiz_state = {
                "current_question": 1,
                "total_questions": min(len(questions), 5),
                "questions": questions[:5], 
                "score": 0,
                "is_active": True
            }
            
            # Use the helper to serve the first question
            return await self._serve_next_quiz_question(quiz_state)
            
        except Exception as e:
            print(f"Error starting quiz: {e}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble creating a quiz right now. Let's continue our regular conversation.", [], {}

    async def handle_quiz_answer(
        self,
        chat_history: List[Dict[str, Any]],
        selected_option: str,
        quiz_state: dict,
        user_id: str,
        chat_title: str,
        learning_goal: Optional[str],
        skills: List[str],
        difficulty: str,
        role: str,
        mentor_topics: Optional[List[str]] = None,
    ) -> Tuple[str, List[str], dict]:
        """Handles a quiz answer, provides feedback, and suggests the next step."""
        if not quiz_state.get("is_active", False):
            return "There is no active quiz. Let's continue our conversation.", ["What's the next topic?"], {}
        
        current_q_index = quiz_state.get("current_question", 1) - 1
        questions = quiz_state.get("questions", [])
        
        if current_q_index >= len(questions):
            return "The quiz is already complete!", ["Let's move on"], quiz_state

        user_answer_letter = selected_option.strip()[0].upper()

        correct_answer = questions[current_q_index].get("correct_answer")
        explanation = questions[current_q_index].get("explanation")
        
        if user_answer_letter == correct_answer:
            quiz_state["score"] += 1
            response = f"✅ **Correct!**\n\n_{explanation}_"
        else:
            response = f"❌ **Incorrect.** The correct answer was **{correct_answer}**.\n\n_{explanation}_"

        quiz_state["current_question"] += 1
        next_q_num = quiz_state["current_question"]

        # Check if the quiz is over to provide final suggestions
        if next_q_num > quiz_state["total_questions"]:
            quiz_state["is_active"] = False
            score = quiz_state["score"]
            total = quiz_state["total_questions"]
            percentage = (score / total) * 100 if total > 0 else 0
            response += f"\n\n**Quiz Complete!**\nYou scored {score}/{total} ({percentage:.0f}%)."
            
            suggestions = [
                "Summarize what we've learned",
                "Move to the next topic",
                "Explain the concepts I got wrong"
            ]
        else:
            # If the quiz is not over, the only suggestion is to continue
            suggestions = ["Next Question"]
        
        return response, suggestions, quiz_state

    def _build_quiz_context(self, learning_goal, skills, difficulty, role, mentor_topics) -> str:
        """Builds system context for quiz generation."""
        context_lines = [f"Role: {role}"]
        if learning_goal: context_lines.append(f"Learning Goal: {learning_goal}")
        if skills: context_lines.append(f"Skills: {', '.join(skills)}")
        context_lines.append(f"Difficulty: {difficulty}")
        if mentor_topics: context_lines.append(f"Topics: {', '.join(mentor_topics)}")
        
        role_instruction = self.prompts["roles"].get(role, self.prompts["roles"]["default"])
        quiz_instruction = self.prompts["shared_components"]["quiz_system_prompt"]
        
        return f"{chr(10).join(context_lines)}\n\n{role_instruction}\n\n{quiz_instruction}"