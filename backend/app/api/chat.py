from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services import agent

router = APIRouter()

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    return await agent.process_chat_message(
        db=db,
        message=request.message,
        session_id=request.session_id or "default-session",
        history=request.history or [],
        pending_booking=request.pending_booking
    )
