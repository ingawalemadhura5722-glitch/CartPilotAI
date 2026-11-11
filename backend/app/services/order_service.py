"""
Checkout logic: cart validation, INR -> USD demo conversion, order creation,
verified capture and cancellation.

Nothing here trusts the browser. The frontend sends product IDs and quantities;
prices, stock, totals, the conversion rate and the USD amount all come from the
database and from backend/.env.
"""

import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, utcnow
from app.models.payment_schemas import (
    CancelResponse,
    CheckoutItem,
    CreateOrderResponse,
    OrderItemOut,
    OrderOut,
    QuoteLine,
    QuoteResponse,
)
from app.models.product import Product
from app.services import paypal_service
from app.services.paypal_service import PayPalServiceError

logger = logging.getLogger("cartpilot.payments")

CAPTURE_LOCK_SECONDS = 120   # a CAPTURING order older than this is considered stuck and may be retried
TWO_PLACES = Decimal("0.01")


class OrderError(Exception):
    """A checkout problem with a user-friendly message and an HTTP status."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        issues: Optional[List[str]] = None,
        order_status: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.issues = issues or []
        self.order_status = order_status


# ======================================================================
# Money helpers (Decimal only, never float arithmetic)
# ======================================================================

def get_demo_rate() -> Decimal:
    """The fixed DEMO rate (INR per 1 USD) from backend/.env. Never from the browser."""
    raw = (os.getenv("PAYPAL_DEMO_INR_PER_USD") or "").strip()
    if not raw:
        raise OrderError(
            "rate_not_configured",
            "The demo conversion rate is not set. Add PAYPAL_DEMO_INR_PER_USD to backend/.env and restart the backend.",
            503,
        )
    try:
        rate = Decimal(raw)
    except InvalidOperation:
        rate = Decimal(0)
    if not rate.is_finite() or rate <= 0 or rate > 100000:
        raise OrderError(
            "rate_invalid",
            "PAYPAL_DEMO_INR_PER_USD in backend/.env must be a positive number such as 85.",
            503,
        )
    return rate


def format_rate(rate: Decimal) -> str:
    return format(rate.normalize(), "f")


def inr_to_paise(price) -> int:
    """Product.price is stored as a float; convert through str() so no float error sneaks in."""
    return int((Decimal(str(price)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def convert_to_usd_cents(total_paise: int, rate: Decimal) -> int:
    total_inr = Decimal(total_paise) / Decimal(100)
    usd = (total_inr / rate).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return int(usd * 100)


def minor_to_str(minor_units: int) -> str:
    """12345 -> '123.45'"""
    return f"{minor_units // 100}.{minor_units % 100:02d}"


def conversion_notice(rate_text: str) -> str:
    return (
        f"Sandbox demo conversion at a fixed rate of ₹{rate_text} = $1.00. "
        "This is not a live exchange rate, and PayPal Sandbox uses test money only."
    )


def _iso(value) -> str:
    return value.isoformat() + "Z"


def _frontend_base_url() -> str:
    raw = (os.getenv("FRONTEND_BASE_URL") or "http://localhost:5173").strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise OrderError("bad_frontend_url", "FRONTEND_BASE_URL in backend/.env is not a valid URL.", 503)
    return raw


# ======================================================================
# Cart quote (validation + totals)
# ======================================================================

@dataclass
class QuoteLineData:
    product: Product
    quantity: int
    unit_paise: int
    line_paise: int


@dataclass
class Quote:
    lines: List[QuoteLineData] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    total_paise: int = 0
    rate: Decimal = Decimal(1)
    usd_cents: int = 0

    @property
    def valid(self) -> bool:
        return not self.issues and bool(self.lines)


def build_quote(db: Session, items: List[CheckoutItem]) -> Quote:
    """Validate the cart against the database and compute the totals."""
    rate = get_demo_rate()

    merged: Dict[int, int] = {}
    for item in items:
        merged[item.product_id] = merged.get(item.product_id, 0) + item.quantity

    products = db.query(Product).filter(Product.id.in_(list(merged.keys()))).all()
    by_id = {p.id: p for p in products}

    quote = Quote(rate=rate)
    for product_id, quantity in merged.items():
        product = by_id.get(product_id)
        if product is None:
            quote.issues.append(f"Product {product_id} no longer exists.")
        elif quantity > 99:
            quote.issues.append(f"You can buy at most 99 units of {product.name}.")
        elif product.stock <= 0:
            quote.issues.append(f"{product.name} is out of stock.")
        elif quantity > product.stock:
            quote.issues.append(
                f"Only {product.stock} unit(s) of {product.name} are available (you asked for {quantity})."
            )
        else:
            unit = inr_to_paise(product.price)
            quote.lines.append(QuoteLineData(product, quantity, unit, unit * quantity))

    quote.total_paise = sum(line.line_paise for line in quote.lines)
    quote.usd_cents = convert_to_usd_cents(quote.total_paise, rate) if quote.total_paise > 0 else 0
    return quote


def quote_to_response(quote: Quote) -> QuoteResponse:
    rate_text = format_rate(quote.rate)
    return QuoteResponse(
        valid=quote.valid,
        issues=quote.issues,
        items=[
            QuoteLine(
                product_id=line.product.id,
                name=line.product.name,
                quantity=line.quantity,
                unit_price_inr=minor_to_str(line.unit_paise),
                line_total_inr=minor_to_str(line.line_paise),
            )
            for line in quote.lines
        ],
        total_inr=minor_to_str(quote.total_paise),
        inr_per_usd=rate_text,
        total_usd=minor_to_str(quote.usd_cents),
        conversion_notice=conversion_notice(rate_text),
    )


# ======================================================================
# Order helpers
# ======================================================================

def order_to_out(order: Order) -> OrderOut:
    return OrderOut(
        order_number=order.order_number,
        status=order.status,
        status_reason=order.status_reason,
        paypal_order_id=order.paypal_order_id,
        paypal_capture_id=order.paypal_capture_id,
        total_inr=minor_to_str(order.total_inr_paise),
        inr_per_usd=order.inr_per_usd,
        total_usd=minor_to_str(order.total_usd_cents),
        currency=order.currency,
        items=[
            OrderItemOut(
                product_id=item.product_id,
                name=item.product_name,
                quantity=item.quantity,
                unit_price_inr=minor_to_str(item.unit_price_paise),
                line_total_inr=minor_to_str(item.unit_price_paise * item.quantity),
            )
            for item in order.items
        ],
        created_at=_iso(order.created_at),
        captured_at=_iso(order.captured_at) if order.captured_at else None,
        conversion_notice=conversion_notice(order.inr_per_usd),
    )


def _set_status(db: Session, order: Order, status: str, reason: Optional[str] = None) -> None:
    order.status = status
    order.status_reason = reason[:300] if reason else None
    order.updated_at = utcnow()
    db.commit()


def _find_order(db: Session, paypal_order_id: str, checkout_token: str) -> Order:
    """
    Find the local order. The same error is used for "unknown order ID" and
    "wrong token", so nobody can probe which PayPal order IDs exist.
    """
    order = db.query(Order).filter(Order.paypal_order_id == paypal_order_id).first()
    if order is None or not secrets.compare_digest(order.checkout_token, checkout_token):
        raise OrderError("order_not_found", "We couldn't find a matching checkout for this payment.", 404)
    return order


# ======================================================================
# 1) Create the order
# ======================================================================

def create_checkout(db: Session, items: List[CheckoutItem]) -> CreateOrderResponse:
    paypal_service.ensure_configured()          # fail early, before saving anything
    quote = build_quote(db, items)

    if not quote.valid:
        raise OrderError(
            "invalid_cart",
            "Some items in your cart can't be purchased right now.",
            422,
            issues=quote.issues or ["Your cart is empty."],
        )
    if quote.usd_cents < 1:
        raise OrderError("amount_too_small", "The cart total is too small to pay with PayPal.", 422)

    base_url = _frontend_base_url()
    rate_text = format_rate(quote.rate)
    order_number = f"CP-{utcnow():%Y%m%d}-{secrets.token_hex(4).upper()}"

    order = Order(
        order_number=order_number,
        checkout_token=secrets.token_urlsafe(24),
        status="CREATING",
        total_inr_paise=quote.total_paise,
        inr_per_usd=rate_text,
        total_usd_cents=quote.usd_cents,
        currency="USD",
    )
    for line in quote.lines:
        order.items.append(
            OrderItem(
                product_id=line.product.id,
                product_name=line.product.name,
                unit_price_paise=line.unit_paise,
                quantity=line.quantity,
            )
        )
    db.add(order)
    db.commit()
    db.refresh(order)

    units = sum(line.quantity for line in quote.lines)
    description = f"CartPilot AI demo order {order_number} ({units} item(s)) - Sandbox INR to USD demo conversion"

    try:
        created = paypal_service.create_order(
            order_number=order_number,
            amount_usd=Decimal(order.total_usd_cents) / Decimal(100),
            description=description,
            return_url=f"{base_url}/payment/success",
            cancel_url=f"{base_url}/payment/cancel",
        )
    except PayPalServiceError as error:
        _set_status(db, order, "FAILED", f"PayPal order creation failed ({error.code})")
        raise

    order.paypal_order_id = created["id"]
    _set_status(db, order, "PENDING")
    logger.info("Created PayPal order %s for %s", created["id"], order_number)

    return CreateOrderResponse(
        order_number=order.order_number,
        paypal_order_id=created["id"],
        approval_url=created["approval_url"],
        checkout_token=order.checkout_token,
        status=order.status,
        total_inr=minor_to_str(order.total_inr_paise),
        inr_per_usd=rate_text,
        total_usd=minor_to_str(order.total_usd_cents),
        conversion_notice=conversion_notice(rate_text),
    )


# ======================================================================
# 2) Capture and VERIFY the payment
# ======================================================================

@dataclass
class _Outcome:
    status: str                       # PAID | PAYMENT_PENDING | FAILED | NEEDS_REVIEW
    reason: Optional[str] = None
    capture_id: Optional[str] = None
    capture_status: Optional[str] = None


def _verify_capture(order: Order, data: dict) -> _Outcome:
    """
    PAID only if ALL of these hold:
      - PayPal order ID and our order number match
      - the order status is COMPLETED
      - there is exactly one COMPLETED capture
      - the currency is USD
      - the captured amount equals the amount WE calculated
    """
    expected = Decimal(order.total_usd_cents) / Decimal(100)

    if data.get("id") != order.paypal_order_id:
        return _Outcome("NEEDS_REVIEW", "PayPal order ID in the response did not match.")

    units = data.get("purchase_units")
    if not isinstance(units, list) or not units or not isinstance(units[0], dict):
        return _Outcome("NEEDS_REVIEW", "PayPal response had no purchase unit.")
    unit = units[0]

    custom_id = unit.get("custom_id")
    if custom_id and custom_id != order.order_number:
        return _Outcome("NEEDS_REVIEW", "PayPal order reference did not match our order.")

    captures = ((unit.get("payments") or {}).get("captures")) or []

    if data.get("status") != "COMPLETED":
        return _Outcome("FAILED", f"PayPal order status is {data.get('status')}.")
    if not captures:
        return _Outcome("NEEDS_REVIEW", "PayPal reported COMPLETED but returned no capture.")

    completed = [c for c in captures if isinstance(c, dict) and c.get("status") == "COMPLETED"]
    if not completed:
        pending = [c for c in captures if isinstance(c, dict) and c.get("status") == "PENDING"]
        if pending:
            return _Outcome("PAYMENT_PENDING", "PayPal is still processing the payment.", pending[0].get("id"), "PENDING")
        first = captures[0] if isinstance(captures[0], dict) else {}
        return _Outcome("FAILED", f"Capture status is {first.get('status')}.", first.get("id"), first.get("status"))

    if len(completed) != 1:
        return _Outcome("NEEDS_REVIEW", "PayPal returned an unexpected number of captures.")

    capture = completed[0]
    capture_id = capture.get("id")
    if not capture_id:
        return _Outcome("NEEDS_REVIEW", "PayPal capture had no ID.")

    amount = capture.get("amount") or {}
    if amount.get("currency_code") != "USD":
        return _Outcome("NEEDS_REVIEW", f"Captured currency was {amount.get('currency_code')}, expected USD.", capture_id, "COMPLETED")
    try:
        paid = Decimal(str(amount.get("value")))
    except InvalidOperation:
        return _Outcome("NEEDS_REVIEW", "Captured amount was unreadable.", capture_id, "COMPLETED")
    if paid != expected:
        return _Outcome(
            "NEEDS_REVIEW",
            f"Captured {paid} USD but expected {expected:.2f} USD.",
            capture_id,
            "COMPLETED",
        )

    return _Outcome("PAID", None, capture_id, "COMPLETED")


@dataclass
class CaptureResult:
    order: Order
    already_captured: bool


_BLOCKED = {
    "CREATING": ("order_not_ready", "This checkout was never completed at PayPal."),
    "CANCELLED": ("order_cancelled", "This checkout was cancelled, so no payment was taken."),
    "FAILED": ("payment_failed", "This payment failed earlier. Nothing was charged. Please start a new checkout."),
    "PAYMENT_PENDING": ("payment_pending", "PayPal is still processing this payment, so the order is not marked as paid yet."),
    "NEEDS_REVIEW": ("needs_review", "This payment needs manual review and is not marked as paid."),
}


def capture_checkout(db: Session, paypal_order_id: str, checkout_token: str) -> CaptureResult:
    order = _find_order(db, paypal_order_id, checkout_token)

    # Duplicate request on an already verified order: return the stored result.
    # PayPal is NOT contacted again.
    if order.status == "PAID":
        return CaptureResult(order, already_captured=True)

    if order.status in _BLOCKED:
        code, message = _BLOCKED[order.status]
        raise OrderError(code, message, 409, order_status=order.status)

    # Atomically claim the capture: only ONE request can move PENDING -> CAPTURING.
    stale_before = utcnow() - timedelta(seconds=CAPTURE_LOCK_SECONDS)
    claimed = (
        db.query(Order)
        .filter(
            Order.id == order.id,
            or_(
                Order.status == "PENDING",
                and_(Order.status == "CAPTURING", Order.updated_at < stale_before),
            ),
        )
        .update({"status": "CAPTURING", "updated_at": utcnow()}, synchronize_session=False)
    )
    db.commit()
    if claimed != 1:
        raise OrderError(
            "capture_in_progress",
            "This payment is already being processed. Please wait a moment and refresh.",
            409,
            order_status="CAPTURING",
        )
    db.refresh(order)

    # ---- Ask PayPal to capture (the customer must already have approved) ----
    try:
        try:
            data = paypal_service.capture_order(order.paypal_order_id, request_id=f"capture-{order.order_number}")
        except PayPalServiceError as error:
            if error.issue == "ORDER_ALREADY_CAPTURED":
                data = paypal_service.get_order(order.paypal_order_id)   # verify what PayPal has
            else:
                raise
    except PayPalServiceError as error:
        if error.issue in ("ORDER_NOT_APPROVED", "PAYER_ACTION_REQUIRED"):
            _set_status(db, order, "PENDING")
            raise OrderError(
                "not_approved",
                "The payment has not been approved in PayPal yet, so nothing was charged. Please approve it and try again.",
                409,
                order_status="PENDING",
            ) from error
        if error.code in ("timeout", "network_error"):
            # We don't know if PayPal captured. A retry is safe (idempotent at PayPal).
            _set_status(db, order, "PENDING", f"Capture not confirmed ({error.code})")
            raise OrderError(
                "capture_unconfirmed",
                "We couldn't confirm the payment with PayPal. Nothing was marked as paid. Please try again.",
                504 if error.code == "timeout" else 502,
                order_status="PENDING",
            ) from error
        if error.code in ("missing_credentials", "invalid_credentials", "not_sandbox"):
            _set_status(db, order, "PENDING", f"Capture not attempted ({error.code})")
            raise
        # PayPal rejected the capture (for example the payment method was declined).
        _set_status(db, order, "FAILED", f"PayPal capture failed ({error.issue or error.code})")
        raise OrderError(
            "capture_failed",
            error.message,
            402 if error.issue == "INSTRUMENT_DECLINED" else 502,
            order_status="FAILED",
        ) from error
    except Exception:
        _set_status(db, order, "PENDING", "Unexpected error during capture")
        raise

    # ---- Verify before believing anything ----
    outcome = _verify_capture(order, data)

    order.paypal_capture_id = outcome.capture_id
    order.paypal_capture_status = outcome.capture_status
    order.status = outcome.status
    order.status_reason = outcome.reason[:300] if outcome.reason else None
    order.updated_at = utcnow()
    if outcome.status == "PAID":
        order.captured_at = utcnow()
    db.commit()
    db.refresh(order)

    if outcome.status == "PAID":
        logger.info("Order %s PAID (capture %s)", order.order_number, order.paypal_capture_id)
        return CaptureResult(order, already_captured=False)

    logger.warning("Order %s NOT paid: %s (%s)", order.order_number, outcome.status, outcome.reason)
    if outcome.status == "PAYMENT_PENDING":
        raise OrderError("payment_pending", _BLOCKED["PAYMENT_PENDING"][1], 409, order_status=outcome.status)
    if outcome.status == "NEEDS_REVIEW":
        raise OrderError(
            "verification_failed",
            "PayPal reported a payment, but it could not be verified automatically. "
            f"The order was NOT marked as paid. Please contact support with order number {order.order_number}.",
            409,
            order_status=outcome.status,
        )
    raise OrderError(
        "payment_failed",
        "PayPal did not complete this payment. Nothing was charged and the order is not paid.",
        402,
        order_status=outcome.status,
    )


# ======================================================================
# 3) Cancel
# ======================================================================

def cancel_checkout(db: Session, paypal_order_id: str, checkout_token: str) -> CancelResponse:
    """Mark a PENDING checkout as CANCELLED. A paid order is never changed."""
    order = _find_order(db, paypal_order_id, checkout_token)

    if order.status == "PENDING":
        _set_status(db, order, "CANCELLED", "Customer cancelled at PayPal")
        return CancelResponse(
            cancelled=True, status=order.status, order_number=order.order_number,
            message="Checkout cancelled. No payment was taken.",
        )

    return CancelResponse(
        cancelled=False, status=order.status, order_number=order.order_number,
        message=f"Order is {order.status}, so it was not changed.",
    )