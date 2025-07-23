# File: interview_bot/core/interview_engine.py
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from config.connections import Connection
from config.prompts import get_system_prompt, GUARDRAILS_PROMPT
from core.question_generator import QuestionGenerator

class InterviewEngine:
    def __init__(self):
        self.connection = Connection()
        self.llm = self.connection.get_llm()
        self.question_generator = QuestionGenerator()
        self.reset_interview()
    
    def reset_interview(self):
        """Reset interview state"""
        self.questions = []
        self.current_question_index = 0
        self.interview_params = {}
        self.start_time = None
        self.answers = []
        self.scores = []
        self.completed = False
        self.question_attempts = {}  # Track attempts per question
        self.question_hints_given = {}  # Track if hint was given for each question
    
    def start_interview(self, category: str, role: str, difficulty: str, num_questions: int, duration: int):
        """Initialize interview with parameters"""
        self.interview_params = {
            "category": category,
            "role": role,
            "difficulty": difficulty,
            "num_questions": num_questions,
            "duration": duration
        }
        
        # Generate questions
        self.questions = self.question_generator.generate_questions(
            category, role, difficulty, num_questions
        )
        
        self.start_time = datetime.now()
        self.current_question_index = 0
        self.completed = False
        self.question_attempts = {}
        self.question_hints_given = {}
        
        return f"""Welcome to your {role.replace('_', ' ').title()} interview!

 **Interview Details:**
- **Role:** {role.replace('_', ' ').title()}
- **Category:** {category.title()}
- **Difficulty:** {difficulty.title()}
- **Questions:** {num_questions}
- **Duration:** {duration} minutes

I'll be evaluating your responses and providing feedback. If you need help, just ask for a hint!

Are you ready to begin? Type 'yes' to start with the first question."""
    
    def get_current_question(self) -> Optional[str]:
        """Get the current question"""
        if self.current_question_index < len(self.questions):
            question_num = self.current_question_index + 1
            total_questions = len(self.questions)
            question = self.questions[self.current_question_index]
            
            return f"**Question {question_num}/{total_questions}:**\n\n{question}"
        return None
    
    def is_time_up(self) -> bool:
        """Check if interview time is up"""
        if not self.start_time:
            return False
        
        elapsed = datetime.now() - self.start_time
        return elapsed.total_seconds() > (self.interview_params["duration"] * 60)
    
    def _is_uncertain_response(self, user_answer: str) -> bool:
        """Check if user response indicates uncertainty or not knowing"""
        uncertain_phrases = [
            "i don't know", "i'm not sure", "i m not sure", "not sure", 
            "dont know", "don't know", "no idea", "not certain",
            "i dont know", "im not sure", "i am not sure",
            "i have no idea", "no clue", "not really sure"
        ]
        
        user_answer_lower = user_answer.lower().strip()
        return any(phrase in user_answer_lower for phrase in uncertain_phrases)
    
    def evaluate_answer(self, user_answer: str) -> str:
        """Evaluate user's answer and provide feedback with hint/skip logic"""
        if self.completed or self.current_question_index >= len(self.questions):
            return "The interview has been completed. Thank you for participating!"
        
        if self.is_time_up():
            self.completed = True
            return "⏰ Time's up! The interview has ended. Thank you for participating!"
        
        current_q_index = self.current_question_index
        current_question = self.questions[current_q_index]
        
        # Initialize tracking for current question if not exists
        if current_q_index not in self.question_attempts:
            self.question_attempts[current_q_index] = 0
            self.question_hints_given[current_q_index] = False
        
        # Check if user is uncertain/doesn't know
        if self._is_uncertain_response(user_answer):
            self.question_attempts[current_q_index] += 1
            
            # Store the uncertain response
            self.answers.append({
                "question": current_question,
                "answer": user_answer,
                "feedback": "User indicated uncertainty",
                "attempt": self.question_attempts[current_q_index]
            })
            
            if self.question_attempts[current_q_index] >= 2:
                # Second "don't know" - skip question
                return self._skip_to_next_question("No problem! I understand this one is challenging. Let's move on to the next question.")
            else:
                # First "don't know" - provide hint
                self.question_hints_given[current_q_index] = True
                hint_response = self.provide_hint()
                return hint_response + "\n\nTake your time and give it a try!"
        
        # Regular answer evaluation
        system_prompt = get_system_prompt(
            self.interview_params["category"],
            self.interview_params["role"],
            self.interview_params["difficulty"]
        )
        
        evaluation_prompt = f"""
        {system_prompt}
        {GUARDRAILS_PROMPT}
        
        Current Question: {current_question}
        Candidate's Answer: {user_answer}
        Previous attempts on this question: {self.question_attempts[current_q_index]}
        Hint already given: {self.question_hints_given[current_q_index]}
        
        Evaluate this answer and respond appropriately:
        
        1. If the answer is correct and complete:
           - Acknowledge the good answer
           - Provide brief positive feedback
           - Say "Let's move to the next question"
           
        2. If the answer is partially correct:
           - Acknowledge what's correct
           - Gently point out what's missing
           - Ask for clarification or additional details
           
        3. If the answer is incorrect:
           - Be encouraging and supportive
           - Provide a hint to guide them toward the right direction
           - Ask them to try again
           
        Be professional, constructive, and encouraging. Your goal is to assess skills while helping the candidate succeed.
        
        Respond now:
        """
        
        try:
            response = self.llm.call(evaluation_prompt)
            
            # Store the answer
            self.answers.append({
                "question": current_question,
                "answer": user_answer,
                "feedback": response,
                "attempt": self.question_attempts[current_q_index] + 1
            })
            
            # Check if we should move to next question
            if self._should_proceed_to_next_question(response):
                return self._move_to_next_question(response)
            
            return response
            
        except Exception as e:
            return f"I apologize, but I'm having trouble processing your answer. Could you please try again? Error: {str(e)}"
    
    def _skip_to_next_question(self, skip_message: str) -> str:
        """Skip current question and move to next"""
        # Mark current question as skipped in answers
        current_question = self.questions[self.current_question_index]
        self.answers.append({
            "question": current_question,
            "answer": "SKIPPED",
            "feedback": "Question was skipped after uncertainty",
            "attempt": self.question_attempts.get(self.current_question_index, 0)
        })
        
        self.current_question_index += 1
        
        # Check if we've reached the end
        if self.current_question_index >= len(self.questions):
            self.completed = True
            return skip_message + "\n\n" + self._generate_final_summary()
        else:
            next_question = self.get_current_question()
            return skip_message + "\n\n" + next_question

    
    def _move_to_next_question(self, current_response: str) -> str:
        """Move to next question after successful answer"""
        self.current_question_index += 1
        
        if self.current_question_index >= len(self.questions):
            self.completed = True
            return current_response + "\n\n" + self._generate_final_summary()
        else:
            next_question = self.get_current_question()
            return current_response + "\n\n" + next_question
    
    def provide_hint(self) -> str:
        """Provide a hint for the current question"""
        if self.current_question_index >= len(self.questions):
            return "No more questions available."
        
        current_question = self.questions[self.current_question_index]
        
        hint_prompt = f"""
        Provide a helpful hint for this interview question without giving away the answer:
        
        Question: {current_question}
        Role: {self.interview_params["role"]}
        Difficulty: {self.interview_params["difficulty"]}
        Category: {self.interview_params["category"]}
        
        Give a hint that guides the candidate toward the right thinking without revealing the answer.
        Be encouraging and supportive. Focus on the key concept or approach they should consider.
        """
        
        try:
            hint = self.llm.call(hint_prompt)
            return f"💡 **Hint:** {hint}"
        except Exception as e:
            return "💡 **Hint:** Think about the core concept this question is testing. Break it down into smaller parts and try a step-by-step approach."
    
    def _should_proceed_to_next_question(self, response: str) -> bool:
        """Determine if we should move to the next question based on the response"""
        proceed_indicators = [
            "next question",
            "move on",
            "let's continue",
            "let's move to",
            "good answer",
            "correct",
            "well done",
            "excellent",
            "great job",
            "perfect",
            "that's right",
            "exactly"
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in proceed_indicators)
    
    # def _generate_final_summary(self) -> str:
    #     """Generate final interview summary"""
    #     total_questions = len(self.questions)

    #     # Count different types of responses
    #     answered_questions = 0
    #     skipped_questions = 0
    #     uncertain_responses = 0

    #     for answer in self.answers:
    #         if answer["answer"] == "SKIPPED":
    #             skipped_questions += 1
    #         elif self._is_uncertain_response(answer["answer"]):
    #             uncertain_responses += 1
    #         else:
    #             answered_questions += 1

    #     # Handle case where questions remain due to early completion
    #     remaining_questions = total_questions - len(self.answers)
    #     if remaining_questions > 0:
    #         skipped_questions += remaining_questions

    #     elapsed_time = datetime.now() - self.start_time if self.start_time else timedelta(0)
    #     hints_used = sum(1 for given in self.question_hints_given.values() if given)

    #     summary = (
    #         "Interview Completed!\n\n"
    #         "Summary:\n"
    #         f"- Role: {self.interview_params['role'].replace('_', ' ').title()}\n"
    #         f"- Total Questions: {total_questions}\n"
    #         f"- Questions Answered: {answered_questions}\n"
    #         f"- Questions Skipped: {skipped_questions}\n"
    #         #f"- Uncertain Responses: {uncertain_responses}\n"
    #         f"- Hints Used: {hints_used}\n"
    #         f"- Time Taken: {int(elapsed_time.total_seconds() // 60)} minutes {int(elapsed_time.total_seconds() % 60)} seconds\n"
    #         f"- Difficulty Level: {self.interview_params['difficulty'].title()}\n\n"
    #         "Performance Analysis:\n"
    #     )

    #     # Calculate completion rate
    #     completion_rate = ((answered_questions / total_questions) * 100) if total_questions > 0 else 0

    #     if completion_rate >= 80:
    #         summary += "- Excellent! You completed most questions successfully."
    #     elif completion_rate >= 60:
    #         summary += "- Good effort! You showed solid understanding in most areas."
    #     elif completion_rate >= 40:
    #         summary += "- Making progress! You demonstrated knowledge in several areas."
    #     else:
    #         summary += "- Keep learning! This interview identified areas for development."

    #     if hints_used > 0:
    #         summary += f"\n- You requested {hints_used} hint(s) - good strategy for learning!"

    #     if skipped_questions > 0:
    #         summary += f"\n- {skipped_questions} question(s) were skipped - consider reviewing these topics."

    #     # if uncertain_responses > 0:
    #     #     summary += f"\n- {uncertain_responses} uncertain response(s) - it's okay to not know everything!"

    #     # Recommendations based on performance
    #     summary += "\n\nRecommendations:"

    #     if completion_rate < 60:
    #         summary += f"\n- Focus on strengthening {self.interview_params['role'].replace('_', ' ')} fundamentals"
    #         summary += f"\n- Practice {self.interview_params['difficulty']} level questions in this area"

    #     if skipped_questions > total_questions // 2:
    #         summary += f"\n- Review core concepts for {self.interview_params['role'].replace('_', ' ')}"
    #         summary += "\n- Consider starting with easier difficulty level next time"

    #     if hints_used == 0 and completion_rate > 80:
    #         summary += "\n- You're ready for a higher difficulty level!"
    #         summary += "\n- Consider trying medium/hard questions next time"

    #     summary += "\n\nThank you for participating! Your responses help you identify strengths and areas for growth."
    #     summary += "\n\nReady for another challenge? Start a new interview!"

    #     return summary

    def _generate_final_summary(self) -> str:
        """Generate final interview summary with accurate counting"""
        total_questions = len(self.questions)
        
        # Simple and accurate counting based on current question index and what was actually completed
        questions_attempted = self.current_question_index
        questions_answered = 0
        questions_skipped = 0
        
        # Count based on question attempts tracking
        for q_idx in range(self.current_question_index):
            if q_idx in self.question_attempts:
                attempts = self.question_attempts[q_idx]
                if attempts >= 2:  # If 2+ attempts (including "I don't know"), it was skipped
                    questions_skipped += 1
                elif attempts == 1:  # If only 1 attempt and we moved on, it was answered
                    questions_answered += 1
            else:
                # If no attempts recorded but we passed this question, it was answered
                questions_answered += 1
        
        elapsed_time = datetime.now() - self.start_time if self.start_time else timedelta(0)
        hints_used = sum(1 for given in self.question_hints_given.values() if given)
        
        summary = f"""
    **Interview Completed**

    **Summary:**
    - **Role:** {self.interview_params["role"].replace('_', ' ').title()}
    - **Total Questions:** {total_questions}
    - **Questions Attempted:** {questions_attempted}
    - **Questions Answered:** {questions_answered}
    - **Questions Skipped:** {questions_skipped}
    - **Hints Used:** {hints_used}
    - **Time Taken:** {int(elapsed_time.total_seconds() // 60)} minutes {int(elapsed_time.total_seconds() % 60)} seconds
    - **Difficulty Level:** {self.interview_params["difficulty"].title()}

    **Performance Analysis:**
    """
        
        # Calculate success rate based on answered vs attempted
        success_rate = ((questions_answered / questions_attempted) * 100) if questions_attempted > 0 else 0
        
        if success_rate >= 80:
            summary += "- **Excellent!** You successfully answered most questions you attempted."
        elif success_rate >= 60:
            summary += "- **Good effort!** You showed solid understanding in most areas."
        elif success_rate >= 40:
            summary += "- **Making progress!** You demonstrated knowledge in several areas."
        else:
            summary += "- **Keep learning!** This interview identified areas for development."
        
        if hints_used > 0:
            summary += f"\n- You requested {hints_used} hint(s)!"
        
        if questions_skipped > 0:
            summary += f"\n- {questions_skipped} question(s) were skipped after uncertainty - consider reviewing these topics."
        
        # Recommendations
        summary += "\n\n**Recommendations:**"
        
        if success_rate < 60:
            summary += f"\n- Focus on strengthening {self.interview_params['role'].replace('_', ' ')} fundamentals"
            summary += f"\n- Practice {self.interview_params['difficulty']} level questions in this area"
        
        if questions_skipped > questions_attempted // 2:
            summary += f"\n- Review core concepts for {self.interview_params['role'].replace('_', ' ')}"
            summary += "\n- Consider starting with easier difficulty level next time"
        
        if hints_used == 0 and success_rate > 80:
            summary += "\n- You're ready for a higher difficulty level!"
            summary += "\n- Consider trying medium/hard questions next time"
        
        summary += "\n\n**Thank you for participating!** Your responses help you identify strengths and areas for growth."
        summary += "\n\n**Ready for another challenge?** Start a new interview with different parameters!"
        
        return summary

    def get_interview_progress(self) -> Dict:
        """Get current interview progress"""
        if not self.questions:
            return {"progress": 0, "current": 0, "total": 0}
        
        return {
            "progress": (self.current_question_index / len(self.questions)) * 100,
            "current": self.current_question_index,
            "total": len(self.questions),
            "attempts": self.question_attempts.get(self.current_question_index, 0),
            "hint_given": self.question_hints_given.get(self.current_question_index, False)
        }
    
    def get_detailed_results(self) -> Dict:
        """Get detailed interview results for analysis"""
        return {
            "interview_params": self.interview_params,
            "questions": self.questions,
            "answers": self.answers,
            "question_attempts": self.question_attempts,
            "hints_given": self.question_hints_given,
            "completed": self.completed,
            "total_time": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }
