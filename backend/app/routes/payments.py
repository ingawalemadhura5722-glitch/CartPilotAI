"""PayPal Sandbox checkout endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payment_schemas import (
    CancelResponse,
    CaptureResponse,
    CheckoutRequest,
    CreateOrderResponse,
    PayPalOrderRef,
    PaymentConfigResponse,
    QuoteResponse,
)
from app.services import order_service, paypal_service
from app.services.order_service import OrderError
from app.services.paypal_service import PayPalServiceError

router = APIRouter(prefix="/api/payments", tags=["Payments (PayPal Sandbox)"])


def _to_http(error: Exception) -> HTTPException:
    """Turn our service errors into clean HTTP errors: {"detail": {"code", "message", ...}}."""
    if isinstance(error, OrderError):
        detail = {"code": error.code, "message": error.message}
        if error.issues:
            detail["issues"] = error.issues
        if error.order_status:
            detail["order_status"] = error.order_status
        return HTTPException(status_code=error.http_status, detail=detail)
    if isinstance(error, PayPalServiceError):
        return HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.message},
        )
    raise error


@router.get("/config", response_model=PaymentConfigResponse)
def payment_config():
    """Public payment settings. Never returns secrets."""
    response = PaymentConfigResponse(
        paypal_configured=paypal_service.is_configured(),
        demo_rate_configured=False,
    )
    try:
        rate = order_service.format_rate(order_service.get_demo_rate())
        response.demo_rate_configured = True
        response.inr_per_usd = rate
        response.conversion_notice = order_service.conversion_notice(rate)
    except OrderError:
        pass
    return response


@router.get("/paypal-status")
def paypal_status():
    """Checks that the PayPal OAuth credentials work. Never returns the token."""
    try:
        paypal_service.check_oauth()
    except PayPalServiceError as error:
        raise _to_http(error)
    return {"oauth_ok": True, "mode": "sandbox"}


@router.post("/quote", response_model=QuoteResponse)
def quote(payload: CheckoutRequest, db: Session = Depends(get_db)):
    """Validate the cart and show the INR total plus the USD Sandbox amount. Creates nothing."""
    try:
        return order_service.quote_to_response(order_service.build_quote(db, payload.items))
    except OrderError as error:
        raise _to_http(error)


@router.post("/create-order", response_model=CreateOrderResponse)
def create_order(payload: CheckoutRequest, db: Session = Depends(get_db)):
    """Re-validate the cart, calculate the USD amount, and create a PayPal Sandbox order."""
    try:
        return order_service.create_checkout(db, payload.items)
    except (OrderError, PayPalServiceError) as error:
        raise _to_http(error)


@router.post("/capture-order", response_model=CaptureResponse)
def capture_order(payload: PayPalOrderRef, db: Session = Depends(get_db)):
    """Capture the approved payment and verify status, currency and amount before marking it paid."""
    try:
        result = order_service.capture_checkout(db, payload.paypal_order_id, payload.checkout_token)
    except (OrderError, PayPalServiceError) as error:
        raise _to_http(error)

    return CaptureResponse(
        success=True,
        already_captured=result.already_captured,
        message=(
            "This payment was already verified earlier. No new capture was made."
            if result.already_captured
            else "Payment captured and verified."
        ),
        order=order_service.order_to_out(result.order),
    )


@router.post("/cancel-order", response_model=CancelResponse)
def cancel_order(payload: PayPalOrderRef, db: Session = Depends(get_db)):
    """Record that the customer cancelled at PayPal. Never touches a paid order."""
    try:
        return order_service.cancel_checkout(db, payload.paypal_order_id, payload.checkout_token)
    except OrderError as error:
        raise _to_http(error)