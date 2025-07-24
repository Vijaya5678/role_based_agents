# interview_assistant/app/api/interview.py
from fastapi import APIRouter, HTTPException, status
from models.interview import InterviewConfig, AnswerSubmission
from services.interview_service import InterviewService

# Create the router
router = APIRouter()
service = InterviewService()

@router.post("/start")
async def start_interview(cfg: InterviewConfig):
    """Start interview endpoint"""
    try:
        session = await service.create_session(cfg)
        return session
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

@router.get("/{sid}/current-question")
async def current_question(sid: str):  # <<< FIX: Changed to async def
    """Get current question endpoint"""
    if sid not in service.active_sessions: # Using active_sessions from service
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    # FIX: Called the correct service method and used await
    return await service.get_current_question(sid)

@router.post("/{sid}/submit-answer")
async def submit_answer(sid: str, submission: AnswerSubmission):
    """Submit answer endpoint"""
    if sid not in service.active_sessions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    # FIX: Called the correct service method
    return await service.process_answer(sid, submission)

@router.get("/{sid}/report")
async def get_report(sid: str):
    """Get report endpoint"""
    if sid not in service.active_sessions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    
    session_data = service.active_sessions[sid]
    session_obj = session_data["session"]
    
    # You can add a check here if you want
    # if session_obj["status"] == "active":
    #     raise HTTPException(status.HTTP_400_BAD_REQUEST, "Interview still running")
        
    # FIX: Called the correct report service and method
    return await service.report_service.generate_report(session_obj, session_data["answers"])