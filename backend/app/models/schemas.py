"""
Pydantic schemas = the shape of data going IN and OUT of the API,
plus the validated "intent" that Gemini extracts from a user message.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductOut(BaseModel):
    """A product as returned by the API (always comes from the database)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    description: str
    price: float
    rating: float
    image_url: str
    stock: int


# ======================================================================
# AI shopping intent (what Gemini extracts from the user's message)
# ======================================================================

IntentType = Literal["search", "compare", "clarify", "general"]
SortPreference = Literal["relevance", "price_low", "rating", "value"]

MAX_BUDGET = 10_000_000


def _clean_text(value) -> Optional[str]:
    """Turn None / '' / 'null' into None, otherwise a trimmed short string."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a"}:
        return None
    return text[:200]


class ShoppingIntent(BaseModel):
    intent: IntentType = "search"
    category: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    brands: List[str] = Field(default_factory=list)
    specs: List[str] = Field(default_factory=list)
    usage: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    sort_preference: SortPreference = "relevance"
    compare_product_ids: List[int] = Field(default_factory=list)
    compare_count: int = 2
    use_previous_products: bool = False
    needs_clarification: bool = False
    clarification_question: Optional[str] = None

    @field_validator("intent", mode="before")
    @classmethod
    def valid_intent(cls, value):
        value = str(value or "").strip().lower()
        return value if value in {"search", "compare", "clarify", "general"} else "search"

    @field_validator("sort_preference", mode="before")
    @classmethod
    def valid_sort(cls, value):
        value = str(value or "").strip().lower()
        return value if value in {"relevance", "price_low", "rating", "value"} else "relevance"

    @field_validator("category", "usage", "clarification_question", mode="before")
    @classmethod
    def clean_optional_text(cls, value):
        return _clean_text(value)

    @field_validator("min_budget", "max_budget", mode="before")
    @classmethod
    def clean_budget(cls, value):
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if 0 < number <= MAX_BUDGET else None

    @field_validator("brands", "specs", "features", "keywords", mode="before")
    @classmethod
    def clean_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        cleaned: List[str] = []
        for item in value:
            text = str(item).strip()[:60]
            if text and text.lower() not in {c.lower() for c in cleaned}:
                cleaned.append(text)
        return cleaned[:8]

    @field_validator("compare_product_ids", mode="before")
    @classmethod
    def clean_ids(cls, value):
        if not isinstance(value, list):
            return []
        ids: List[int] = []
        for item in value:
            try:
                number = int(item)
            except (TypeError, ValueError):
                continue
            if number not in ids:
                ids.append(number)
        return ids[:4]

    @field_validator("compare_count", mode="before")
    @classmethod
    def clean_count(cls, value):
        try:
            return max(2, min(4, int(value)))
        except (TypeError, ValueError):
            return 2

    @model_validator(mode="after")
    def order_budgets(self):
        # If the AI swapped min and max, fix it.
        if self.min_budget and self.max_budget and self.min_budget > self.max_budget:
            self.min_budget, self.max_budget = self.max_budget, self.min_budget
        return self


# ======================================================================
# Chat
# ======================================================================

class ChatHistoryMessage(BaseModel):
    """One earlier message, sent by the frontend so the AI has context."""

    role: Literal["user", "assistant"]
    text: str = Field(..., min_length=1, max_length=1500)
    # IDs of products shown in this message (only meaningful for assistant messages).
    product_ids: List[int] = Field(default_factory=list, max_length=8)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, examples=["Find me a laptop under ₹60,000 for programming."])
    history: List[ChatHistoryMessage] = Field(default_factory=list, max_length=20)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


class ComparisonItem(BaseModel):
    """One column of a comparison. Price/rating/stock come from the database."""

    product_id: int
    name: str
    price: float
    rating: float
    stock: int
    in_stock: bool
    key_specs: List[str] = Field(default_factory=list)
    advantages: List[str] = Field(default_factory=list)
    disadvantages: List[str] = Field(default_factory=list)
    best_for: str = ""
    is_winner: bool = False


class ComparisonOut(BaseModel):
    criterion: str
    winner_product_id: Optional[int] = None
    items: List[ComparisonItem]


class ChatResponse(BaseModel):
    reply: str
    products: List[ProductOut] = Field(default_factory=list)
    # "gemini" for the real assistant, "demo-rule-based" for /api/chat/demo.
    mode: str = "gemini"
    model: Optional[str] = None
    intent: Optional[ShoppingIntent] = None          # what the AI understood (useful for testing)
    comparison: Optional[ComparisonOut] = None
    needs_clarification: bool = False
    suggestions: List[str] = Field(default_factory=list)
    warning: Optional[str] = None


# ======================================================================
# Cart validation (unchanged from Day 1)
# ======================================================================

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
    server_price: Optional[float] = None
    available_stock: Optional[int] = None
    line_total: float
    valid: bool
    issues: List[str] = []


class CartValidateResponse(BaseModel):
    valid: bool
    items: List[CartLineResult]
    subtotal: float
    total: float
    currency: str = "INR"
    message: str