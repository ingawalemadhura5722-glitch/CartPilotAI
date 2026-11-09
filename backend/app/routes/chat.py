"""Demo chat endpoint (rule-based, no LLM)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import get_recommendations

router = APIRouter(prefix="/api", tags=["Chat (demo)"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """Accept a user message and return matching products using simple rules."""
    reply, products = get_recommendations(db, payload.message)
    return ChatResponse(reply=reply, products=products)