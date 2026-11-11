"""Chat endpoints: the real Gemini assistant, plus the Day 1 rule-based demo."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import ChatRequest, ChatResponse, ProductOut
from app.services import rule_based_service
from app.services.chat_service import handle_chat
from app.services.gemini_client import GeminiServiceError, get_model_name, is_configured

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    AI shopping assistant (Gemini + database).
    Send the new message and, optionally, the recent conversation in `history`.
    """
    try:
        return handle_chat(db, payload.message, payload.history)
    except GeminiServiceError as error:
        # detail is an object: {"code": "...", "message": "..."}
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.message},
        )


@router.get("/chat/status")
def chat_status():
    """Tells you whether a Gemini key is configured (never returns the key itself)."""
    return {"gemini_configured": is_configured(), "model": get_model_name()}


@router.post("/chat/demo", response_model=ChatResponse, tags=["Chat (Day 1 demo)"])
def chat_demo(payload: ChatRequest, db: Session = Depends(get_db)):
    """The Day 1 rule-based assistant, kept for comparison. No AI involved."""
    reply, products = rule_based_service.get_recommendations(db, payload.message)
    return ChatResponse(
        reply=reply,
        products=[ProductOut.model_validate(p) for p in products],
        mode="demo-rule-based",
    )