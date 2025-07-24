# app/services/interview_service.py
import uuid
from datetime import datetime, timedelta
from interview_assistant.app.config.prompts import DIFFICULTY_CONFIG
from interview_assistant.app.services.question_service import QuestionService
from interview_assistant.app.services.evaluation_service import EvaluationService
from interview_assistant.app.services.report_service import ReportService

class InterviewService:
    def __init__(self):
        self.active_sessions = {}  # Simple in-memory sessions; replace with DB for prod
        self.question_service = QuestionService()
        self.evaluation_service = EvaluationService()
        self.report_service = ReportService()

    async def create_session(self, config):
        session_id = str(uuid.uuid4())
        diff_cfg = DIFFICULTY_CONFIG[config.difficulty]
        questions = await self.question_service.generate_questions(
            category=config.category,
            role=config.role,
            difficulty=config.difficulty,
            num_questions=diff_cfg["num_questions"]
        )
        session = {
            "session_id": session_id,
            "config": config,
            "questions": questions,
            "current_question_index": 0,
            "start_time": datetime.utcnow(),
            "time_limit_minutes": diff_cfg["time_minutes"],
            "status": "active"
        }
        self.active_sessions[session_id] = {
            "session": session,
            "answers": [],
            "hints_used": 0,
            "skipped_questions": 0,
            "additional_questions_offered": False,
        }
        return session

    def _is_time_expired(self, session):
        elapsed = datetime.utcnow() - session["start_time"]
        return elapsed > timedelta(minutes=session["time_limit_minutes"])

    def _get_time_remaining(self, session):
        elapsed = datetime.utcnow() - session["start_time"]
        remaining = timedelta(minutes=session["time_limit_minutes"]) - elapsed
        return max(0, int(remaining.total_seconds()))

    async def get_current_question(self, session_id):
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session id")

        sess_data = self.active_sessions[session_id]
        session = sess_data["session"]

        if self._is_time_expired(session):
            session["status"] = "expired"
            return {"message": "Time expired. Interview ended."}

        idx = session["current_question_index"]
        if idx >= len(session["questions"]):
            return {"message": "No more questions. You may want to request additional questions or end."}

        question = session["questions"][idx]
        time_remaining = self._get_time_remaining(session)
        return {
            "question_number": idx + 1,
            "total_questions": len(session["questions"]),
            "question_text": question,
            "time_remaining": time_remaining
        }

    async def process_answer(self, session_id, submission):
        if session_id not in self.active_sessions:
            raise ValueError("Session not found or expired")

        sess_data = self.active_sessions[session_id]
        session = sess_data["session"]

        if session["status"] != "active":
            return {"message": "Interview session is not active."}

        if self._is_time_expired(session):
            session["status"] = "expired"
            report = await self.report_service.generate_report(session, sess_data["answers"])
            return {"message": "Time expired. Interview ended.", "report": report}

        action = submission.action

        if action == "hint":
            # Provide a brief hint for current question
            hint = await self.evaluation_service.generate_hint(
                session["questions"][session["current_question_index"]],
                session["config"]
            )
            sess_data["hints_used"] += 1
            return {"hint": hint}

        elif action == "skip":
            # Move to next question and record skip
            sess_data["skipped_questions"] += 1
            session["current_question_index"] += 1
            next_question = await self.get_current_question(session_id)
            return {"message": "Question skipped.", "next_question": next_question}

        elif action == "end":
            # End interview immediately and generate report
            session["status"] = "completed"
            report = await self.report_service.generate_report(session, sess_data["answers"])
            return {"message": "Interview ended by user.", "report": report}

        elif action == "submit":
            answer = submission.answer or ""
            question = session["questions"][session["current_question_index"]]
            evaluation = await self.evaluation_service.evaluate_answer(question, answer, session["config"])
            sess_data["answers"].append({
                "question": question,
                "answer": answer,
                "evaluation": evaluation,
                "timestamp": datetime.utcnow().isoformat()
            })

            session["current_question_index"] += 1

            # Check if all questions asked
            if session["current_question_index"] >= len(session["questions"]):
                time_remaining = self._get_time_remaining(session)
                # Offer more questions only once if time remains more than 5 mins
                if time_remaining > 300 and not sess_data["additional_questions_offered"]:
                    sess_data["additional_questions_offered"] = True
                    return {
                        "message": "You've completed all questions with time remaining. Do you want more questions? (yes/no)",
                        "action_required": "user_choice"
                    }
                else:
                    session["status"] = "completed"
                    report = await self.report_service.generate_report(session, sess_data["answers"])
                    return {"message": "Interview completed.", "report": report}

            # Return next question
            next_question = await self.get_current_question(session_id)
            return {"next_question": next_question, "evaluation": evaluation}

        else:
            return {"message": f"Unknown action '{action}'"}

    async def handle_additional_questions_response(self, session_id, user_response: str):
        """
        If user replies 'yes' for more questions, add more questions accordingly;
        else end the interview.
        """
        if session_id not in self.active_sessions:
            raise ValueError("Session not found or expired")

        sess_data = self.active_sessions[session_id]
        session = sess_data["session"]

        if user_response.strip().lower() == "yes":
            # Generate 3 more questions at same difficulty
            extra_questions = await self.question_service.generate_questions(
                category=session["config"].category,
                role=session["config"].role,
                difficulty=session["config"].difficulty,
                num_questions=3,
            )
            session["questions"].extend(extra_questions)
            return await self.get_current_question(session_id)
        else:
            session["status"] = "completed"
            report = await self.report_service.generate_report(session, sess_data["answers"])
            return {"message": "Interview ended per user request.", "report": report}

