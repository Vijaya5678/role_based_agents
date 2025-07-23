# File: interview_bot/core/question_generator.py
from typing import List, Dict
from interview_assistant.config.connections import Connection
from interview_assistant.config.prompts import get_system_prompt, GUARDRAILS_PROMPT

class QuestionGenerator:
    def __init__(self):
        self.connection = Connection()
        self.llm = self.connection.get_llm()
    
    def generate_questions(self, category: str, role: str, difficulty: str, num_questions: int) -> List[str]:
        """Generate interview questions based on parameters"""
        system_prompt = get_system_prompt(category, role, difficulty)
        
        prompt = f"""
        {system_prompt}
        {GUARDRAILS_PROMPT}
        
        Generate exactly {num_questions} interview questions for a {role} position at {difficulty} difficulty level.
        
        Requirements:
        - Questions should be appropriate for {difficulty} level
        - Focus on {category} skills for {role}
        - Make questions clear and specific
        - Return only the questions, numbered 1-{num_questions}
        
        Generate the questions now:
        """
        
        try:
            response = self.llm.call(prompt)
            questions = self._parse_questions(response, num_questions)
            return questions
        except Exception as e:
            print(f"Error generating questions: {e}")
            return self._get_fallback_questions(category, role, difficulty, num_questions)
    
    def _parse_questions(self, response: str, expected_count: int) -> List[str]:
        """Parse questions from LLM response"""
        lines = response.strip().split('\n')
        questions = []
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('Q')):
                # Remove numbering
                if '. ' in line:
                    question = line.split('. ', 1)[1]
                elif ') ' in line:
                    question = line.split(') ', 1)[1]
                else:
                    question = line
                
                if question.strip():
                    questions.append(question.strip())
        
        return questions[:expected_count]
    
    def _get_fallback_questions(self, category: str, role: str, difficulty: str, num_questions: int) -> List[str]:
        """Fallback questions if generation fails"""
        fallback = {
            "technical": {
                "python_developer": [
                    "What is the difference between a list and a tuple in Python?",
                    "How do you handle exceptions in Python?",
                    "Explain the concept of object-oriented programming.",
                    "What are Python decorators and how do you use them?",
                    "How would you optimize a slow Python script?"
                ]
            },
            "non_technical": {
                "hr_manager": [
                    "How do you handle conflicts between team members?",
                    "Describe your approach to performance management.",
                    "How do you ensure diversity in hiring?",
                    "What strategies do you use for employee retention?",
                    "How do you handle difficult conversations with employees?"
                ]
            }
        }
        
        questions = fallback.get(category, {}).get(role, [
            f"Tell me about your experience with {role}.",
            f"What challenges have you faced in {role} roles?",
            f"How do you stay updated with {role} trends?",
            f"Describe a successful project in {role}.",
            f"What skills are most important for a {role}?"
        ])
        
        return questions[:num_questions]
