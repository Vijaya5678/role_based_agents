# interview_assistant/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Fix: Import from the correct path
from api import interview as interview_router

app = FastAPI(
    title="Interview Assistant API",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fix: Mount at the correct prefix to match your frontend calls
app.include_router(interview_router.router, prefix="/api/interview")

@app.get("/")
async def root():
    return {"message": "Interview Assistant API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

