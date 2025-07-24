# app/services/report_service.py
from datetime import datetime
from interview_assistant.app.utils.llm_client import LLMClient

class ReportService:
    def __init__(self):
        self.llm_client = LLMClient()

    async def generate_report(self, session, answers):
        """
        Generate comprehensive report after quiz completion.
        """
        # Build question-by-question summary string
        summary = ""
        for i, ans in enumerate(answers, 1):
            summary += (
                f"Q{i}: {ans['question']}\n"
                f"Answer: {ans['answer']}\n"
                f"Score: {ans['evaluation']['score']}\n"
                f"Feedback: {ans['evaluation']['feedback']}\n\n"
            )

        overall_prompt = f"""
        Analyze the overall interview performance for a {session.config.role} position
        with difficulty level {session.config.difficulty}.

        Question Summary:
        {summary}

        Provide an overall score (1-10), strengths, weaknesses, and areas for improvement.
        """

        overall_evaluation = await self.llm_client.generate_report(overall_prompt)

        report = {
            "session_info": {
                "role": session.config.role,
                "category": session.config.category,
                "difficulty": session.config.difficulty,
                "total_time_minutes": (datetime.utcnow() - session.start_time).total_seconds() / 60,
                "questions_attempted": len(answers),
                "total_questions": len(session.questions),
            },
            "questions": answers,
            "final_evaluation": overall_evaluation,
            "generated_at": datetime.utcnow().isoformat()
        }

        return report
