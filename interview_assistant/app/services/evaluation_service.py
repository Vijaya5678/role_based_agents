# app/services/evaluation_service.py
from utils.llm_client import LLMClient

class EvaluationService:
    def __init__(self):
        self.llm = LLMClient()

    async def evaluate_answer(self, question: str, answer: str, config):
        evaluation = await self.llm.evaluate_answer(question, answer, config.dict())
        return evaluation

    async def generate_hint(self, question: str, config):
        hint = await self.llm.generate_hint(question, config.dict())
        return hint

