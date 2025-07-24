# app/services/question_service.py
from interview_assistant.app.utils.llm_client import LLMClient
from interview_assistant.app.config.prompts import INTERVIEW_PROMPT_TEMPLATE, DIFFICULTY_CONFIG

class QuestionService:
    def __init__(self):
        self.llm = LLMClient()

    # In question_service.py - this should work now
    async def generate_questions(self, category: str, role: str, difficulty: str, num_questions: int):
        prompt = INTERVIEW_PROMPT_TEMPLATE.format(
            category=category,
            role=role,
            difficulty=difficulty,
            num_questions=num_questions,
            time_minutes=DIFFICULTY_CONFIG[difficulty]["time_minutes"],
            question_complexity=DIFFICULTY_CONFIG[difficulty]["question_complexity"],
            evaluation_criteria=DIFFICULTY_CONFIG[difficulty]["evaluation_criteria"],
            hint_frequency=DIFFICULTY_CONFIG[difficulty]["hint_frequency"],
        )
        generated_questions = await self.llm.generate_questions(prompt)
        return generated_questions[:num_questions]

