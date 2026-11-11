"""Request/response shapes for the payment endpoints."""

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# PayPal order IDs are short upper-case/digit strings. We reject anything else.
PAYPAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


# ---------- Requests ----------

class CheckoutItem(BaseModel):
    product_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1, le=99)


class CheckoutRequest(BaseModel):
    """
    ONLY product IDs and quantities are used. If a client also sends "price",
    "total", "amount" or "rate", those fields are ignored by the backend.
    """

    items: List[CheckoutItem] = Field(..., min_length=1, max_length=50)


class PayPalOrderRef(BaseModel):
    paypal_order_id: str
    checkout_token: str = Field(..., min_length=10, max_length=100)

    @field_validator("paypal_order_id")
    @classmethod
    def valid_paypal_id(cls, value: str) -> str:
        value = value.strip()
        if not PAYPAL_ID_PATTERN.match(value):
            raise ValueError("Invalid PayPal order ID")
        return value


# ---------- Responses ----------

class QuoteLine(BaseModel):
    product_id: int
    name: str
    quantity: int
    unit_price_inr: str
    line_total_inr: str


class QuoteResponse(BaseModel):
    valid: bool
    issues: List[str]
    items: List[QuoteLine]
    total_inr: str                 # original total in INR (string, 2 decimals)
    inr_per_usd: str               # the DEMO rate configured on the server
    total_usd: str                 # USD Sandbox amount (string, 2 decimals)
    currency: str = "USD"
    conversion_notice: str


class CreateOrderResponse(BaseModel):
    order_number: str
    paypal_order_id: str
    approval_url: str
    checkout_token: str
    status: str
    total_inr: str
    inr_per_usd: str
    total_usd: str
    currency: str = "USD"
    conversion_notice: str


class OrderItemOut(BaseModel):
    product_id: int
    name: str
    quantity: int
    unit_price_inr: str
    line_total_inr: str


class OrderOut(BaseModel):
    order_number: str
    status: str
    status_reason: Optional[str] = None
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    total_inr: str
    inr_per_usd: str
    total_usd: str
    currency: str
    items: List[OrderItemOut]
    created_at: str
    captured_at: Optional[str] = None
    conversion_notice: str


class CaptureResponse(BaseModel):
    success: bool
    already_captured: bool
    message: str
    order: OrderOut


class CancelResponse(BaseModel):
    cancelled: bool
    status: str
    order_number: str
    message: str


class PaymentConfigResponse(BaseModel):
    sandbox: bool = True
    currency: str = "USD"
    paypal_configured: bool
    demo_rate_configured: bool
    inr_per_usd: Optional[str] = None
    conversion_notice: Optional[str] = None