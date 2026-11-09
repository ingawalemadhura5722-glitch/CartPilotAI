"""
Pydantic schemas = the shape of data going IN and OUT of the API.
FastAPI uses them to validate requests and to build the Swagger docs.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductOut(BaseModel):
    """A product as returned by the API."""

    # from_attributes lets Pydantic read data straight from a SQLAlchemy object.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    description: str
    price: float
    rating: float
    image_url: str
    stock: int


# ---------- Chat ----------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, examples=["Find me a laptop under ₹60,000 for programming."])


class ChatResponse(BaseModel):
    reply: str
    products: List[ProductOut]
    # Tells the frontend this is NOT a real LLM. Will change in a later day.
    mode: str = "demo-rule-based"


# ---------- Cart validation ----------

class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1, le=99)
    price: float = Field(..., ge=0, description="The unit price the client believes the product costs")


class CartValidateRequest(BaseModel):
    items: List[CartItemIn] = Field(..., min_length=1)


class CartLineResult(BaseModel):
    product_id: int
    name: Optional[str] = None
    quantity: int
    client_price: float
    server_price: Optional[float] = None     # None if the product does not exist
    available_stock: Optional[int] = None
    line_total: float                         # server_price * quantity (0 if not found)
    valid: bool
    issues: List[str] = []


class CartValidateResponse(BaseModel):
    valid: bool
    items: List[CartLineResult]
    subtotal: float
    total: float
    currency: str = "INR"
    message: str