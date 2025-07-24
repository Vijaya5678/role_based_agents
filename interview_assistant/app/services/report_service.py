# app/services/report_service.py
import json
from datetime import datetime
from utils.llm_client import LLMClient

class ReportService:
    def __init__(self):
        self.llm_client = LLMClient()

    async def generate_report(self, session, answers):
        """
        Generate comprehensive report after quiz completion.
        'session' is the InterviewSession Pydantic model.
        """
        summary = ""
        for i, ans in enumerate(answers, 1):
            summary += (
                f"Q{i}: {ans['question']}\n"
                f"Answer: {ans.get('answer', 'Not answered')}\n"
                f"Score: {ans.get('evaluation', {}).get('score', 'N/A')}\n"
                f"Feedback: {ans.get('evaluation', {}).get('feedback', 'N/A')}\n\n"
            )

        # FIX: Access Pydantic model attributes correctly (e.g., session.config.role)
        overall_prompt = f"""
        Analyze the overall interview performance for a {session.config.role} position
        with difficulty level {session.config.difficulty}.

        Question-by-Question Summary:
        {summary}

        Based on the summary, provide a final evaluation. Your entire response MUST be a single JSON object with the following keys:
        - "overall_score": An integer score from 1 to 10.
        - "strengths": A string summarizing the candidate's strengths.
        - "areas_for_improvement": A string summarizing the candidate's areas for improvement.
        
        Example JSON:
        {{
            "overall_score": 7,
            "strengths": "Demonstrated solid understanding of core concepts and provided clear answers to several questions.",
            "areas_for_improvement": "Could provide more detailed examples in practical scenarios and should review advanced topics."
        }}
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