# app/services/interview_service.py
import uuid
from datetime import datetime, timedelta
from interview_assistant.app.config.prompts import DIFFICULTY_CONFIG
from interview_assistant.app.models.interview import InterviewSession
from interview_assistant.app.services.question_service import QuestionService
from interview_assistant.app.services.evaluation_service import EvaluationService
from interview_assistant.app.services.report_service import ReportService

class InterviewService:
    def __init__(self):
        self.active_sessions = {}
        self.question_service = QuestionService()
        self.evaluation_service = EvaluationService()
        self.report_service = ReportService()

    async def create_session(self, config):
        session_id = str(uuid.uuid4())
        diff_cfg = DIFFICULTY_CONFIG[config.difficulty]
        
        print(f"Creating session for: {config.category}, {config.role}, {config.difficulty}")
        
        questions = await self.question_service.generate_questions(
            category=config.category,
            role=config.role,
            difficulty=config.difficulty,
            num_questions=diff_cfg["num_questions"]
        )
        
        print(f"Generated {len(questions)} questions")

        session = InterviewSession(
            session_id=session_id,
            config=config,
            questions=questions,
            current_question_index=0,
            start_time=datetime.utcnow(),
            time_limit_minutes=diff_cfg["time_minutes"],
            status="active"
        )
        
        self.active_sessions[session_id] = {
            "session": session,
            "answers": [],
            "hints_used": 0,
            "skipped_questions": 0,
        }
        
        print(f"Session created with ID: {session_id}")
        return session

    def _is_time_expired(self, session: InterviewSession):
        elapsed = datetime.utcnow() - session.start_time
        return elapsed > timedelta(minutes=session.time_limit_minutes)

    def _get_time_remaining(self, session: InterviewSession):
        elapsed = datetime.utcnow() - session.start_time
        remaining = timedelta(minutes=session.time_limit_minutes) - elapsed
        return max(0, int(remaining.total_seconds()))

    async def get_current_question(self, session_id):
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session id")

        session = self.active_sessions[session_id]["session"]

        if self._is_time_expired(session):
            session.status = "expired"
            return {"message": "Time expired. Interview ended."}

        idx = session.current_question_index
        if idx >= len(session.questions):
            return {"message": "All questions completed."}

        return {
            "question_number": idx + 1,
            "total_questions": len(session.questions),
            "question_text": session.questions[idx],
            "time_remaining": self._get_time_remaining(session)
        }

    async def process_answer(self, session_id, submission):
        if session_id not in self.active_sessions:
            raise ValueError("Session not found or expired")

        sess_data = self.active_sessions[session_id]
        session = sess_data["session"]

        if session.status != "active":
            return {"message": "Interview session is not active."}

        if self._is_time_expired(session):
            session.status = "expired"
            report = await self.report_service.generate_report(session, sess_data["answers"])
            return {"message": "Time expired. Interview ended.", "report": report}
        
        action = submission.action
        current_question_text = session.questions[session.current_question_index]

        if action == "hint":
            hint = await self.evaluation_service.generate_hint(current_question_text, session.config)
            sess_data["hints_used"] += 1
            return {"hint": hint}

        if action == "end":
            session.status = "completed"
            report = await self.report_service.generate_report(session, sess_data["answers"])
            return {"message": "Interview ended by user.", "report": report}

        if action == "skip":
            evaluation = {"score": 0, "verdict": "skipped", "feedback": "Question was skipped."}
            answer = ""
            sess_data["skipped_questions"] += 1
        elif action == "submit":
            answer = submission.answer or ""
            evaluation = await self.evaluation_service.evaluate_answer(current_question_text, answer, session.config)

        sess_data["answers"].append({
            "question": current_question_text,
            "answer": answer,
            "evaluation": evaluation,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        session.current_question_index += 1

        if session.current_question_index >= len(session.questions):
            session.status = "completed"
            report = await self.report_service.generate_report(session, sess_data["answers"])
            return {"message": "Interview completed.", "report": report, "evaluation": evaluation}

        next_question = await self.get_current_question(session_id)
        return {"next_question": next_question, "evaluation": evaluation}