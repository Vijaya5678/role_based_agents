# app/models/interview.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class InterviewConfig(BaseModel):
    category: str
    role: str
    difficulty: str

class InterviewSession(BaseModel):
    session_id: str
    config: InterviewConfig
    questions: List[str]
    current_question_index: int
    start_time: datetime
    time_limit_minutes: int
    status: str  # "active", "completed", "expired"

class AnswerSubmission(BaseModel):
    session_id: str
    answer: str
    action: str  # "submit", "hint", "skip", "end"

class QuestionResponse(BaseModel):
    question_number: int
    total_questions: int
    question_text: str
    evaluation: Optional[str] = None
    hint: Optional[str] = None
    time_remaining: int
