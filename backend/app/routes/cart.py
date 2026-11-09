"""Cart endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import CartValidateRequest, CartValidateResponse
from app.services.cart_service import validate_cart

router = APIRouter(prefix="/api/cart", tags=["Cart"])


@router.post("/validate", response_model=CartValidateResponse)
def validate(payload: CartValidateRequest, db: Session = Depends(get_db)):
    """Check product IDs, quantities, stock and prices against the database."""
    return validate_cart(db, payload.items)