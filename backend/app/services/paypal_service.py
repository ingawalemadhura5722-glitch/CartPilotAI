"""
PayPal REST API client (SANDBOX ONLY). This is the only file that talks to PayPal.

- OAuth token is requested with the Client ID + Secret and kept in memory only.
  It is never logged, returned by the API, or sent to the browser.
- Every failure becomes a PayPalServiceError with a friendly message.
- Only PayPal's debug_id and issue code are logged. Never secrets, tokens or request bodies.
"""

import logging
import os
import re
import threading
import time
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("cartpilot.paypal")

SANDBOX_HOST = "api-m.sandbox.paypal.com"
DEFAULT_BASE_URL = f"https://{SANDBOX_HOST}"
_PLACEHOLDER_PREFIXES = ("your_", "existing_", "changeme")
_ORDER_ID_RE = re.compile(r"^[A-Za-z0-9\-]{8,64}$")

_FRIENDLY_ISSUES = {
    "INSTRUMENT_DECLINED": "PayPal declined the selected payment method. Please try again with a different one.",
    "ORDER_NOT_APPROVED": "The order has not been approved in PayPal yet.",
    "PAYER_ACTION_REQUIRED": "The customer still needs to approve the payment in PayPal.",
    "ORDER_ALREADY_CAPTURED": "This PayPal order has already been captured.",
    "INVALID_RESOURCE_ID": "PayPal could not find this order.",
}


class PayPalServiceError(Exception):
    """A problem talking to PayPal, with a user-friendly message and an HTTP status."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 502,
        issue: Optional[str] = None,
        debug_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.issue = issue          # PayPal's own issue code, e.g. ORDER_ALREADY_CAPTURED
        self.debug_id = debug_id


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

def _timeout() -> float:
    try:
        return max(5.0, float(os.getenv("PAYPAL_TIMEOUT_SECONDS", "20")))
    except ValueError:
        return 20.0


def _credentials() -> Tuple[str, str]:
    client_id = (os.getenv("PAYPAL_CLIENT_ID") or "").strip()
    secret = (os.getenv("PAYPAL_CLIENT_SECRET") or "").strip()
    for value in (client_id, secret):
        if not value or value.lower().startswith(_PLACEHOLDER_PREFIXES):
            raise PayPalServiceError(
                "missing_credentials",
                "PayPal is not configured. Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET to backend/.env and restart the backend.",
                503,
            )
    return client_id, secret


def _base_url() -> str:
    raw = (os.getenv("PAYPAL_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or parsed.hostname != SANDBOX_HOST:
        raise PayPalServiceError(
            "not_sandbox",
            "This app only supports the PayPal Sandbox. Set PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com in backend/.env.",
            503,
        )
    return raw


def ensure_configured() -> None:
    _credentials()
    _base_url()


def is_configured() -> bool:
    try:
        ensure_configured()
        return True
    except PayPalServiceError:
        return False


# ----------------------------------------------------------------------
# OAuth token (kept in memory only)
# ----------------------------------------------------------------------

_token_lock = threading.Lock()
_token: Dict[str, Any] = {"value": None, "expires_at": 0.0}


def _get_token(force: bool = False) -> str:
    client_id, secret = _credentials()
    base = _base_url()

    with _token_lock:
        if not force and _token["value"] and time.time() < _token["expires_at"] - 60:
            return _token["value"]

        _token["value"] = None
        try:
            with httpx.Client(timeout=_timeout()) as client:
                response = client.post(
                    f"{base}/v1/oauth2/token",
                    auth=(client_id, secret),
                    data={"grant_type": "client_credentials"},
                    headers={"Accept": "application/json"},
                )
        except httpx.TimeoutException as exc:
            raise PayPalServiceError("timeout", "PayPal took too long to respond. Please try again.", 504) from exc
        except httpx.HTTPError as exc:
            raise PayPalServiceError("network_error", "Could not reach PayPal. Check the internet connection.", 502) from exc

        if response.status_code in (400, 401, 403):
            raise PayPalServiceError(
                "invalid_credentials",
                "PayPal rejected the Client ID or Secret. Check PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in backend/.env.",
                503,
            )
        if response.status_code >= 400:
            logger.warning("PayPal token request failed with HTTP %s", response.status_code)
            raise PayPalServiceError("paypal_error", "PayPal is temporarily unavailable. Please try again.", 502)

        try:
            data = response.json()
            token = data["access_token"]
            expires_in = float(data.get("expires_in", 300))
        except (ValueError, KeyError, TypeError) as exc:
            raise PayPalServiceError("paypal_error", "PayPal returned an unexpected response.", 502) from exc

        _token["value"] = token
        _token["expires_at"] = time.time() + expires_in
        return token


def check_oauth() -> None:
    """Used by the status endpoint: proves the credentials work. Returns nothing sensitive."""
    ensure_configured()
    _get_token(force=True)


# ----------------------------------------------------------------------
# Generic request helper
# ----------------------------------------------------------------------

def _error_from_response(response: httpx.Response) -> PayPalServiceError:
    debug_id = response.headers.get("paypal-debug-id")
    issue: Optional[str] = None
    try:
        body = response.json()
    except ValueError:
        body = {}

    if isinstance(body, dict):
        debug_id = body.get("debug_id") or debug_id
        details = body.get("details")
        if isinstance(details, list) and details and isinstance(details[0], dict):
            issue = details[0].get("issue")
        issue = issue or body.get("name")

    logger.warning("PayPal API error: HTTP %s issue=%s debug_id=%s", response.status_code, issue, debug_id)

    message = _FRIENDLY_ISSUES.get(issue or "", "PayPal could not process the request. Please try again.")
    status = 502
    if issue == "INVALID_RESOURCE_ID" or response.status_code == 404:
        status = 404
    elif issue == "INSTRUMENT_DECLINED":
        status = 402
    return PayPalServiceError("paypal_error", message, status, issue=issue, debug_id=debug_id)


def _request(
    method: str,
    path: str,
    json_body: Optional[Dict[str, Any]] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    base = _base_url()
    response: Optional[httpx.Response] = None

    for attempt in range(2):
        token = _get_token(force=(attempt == 1))
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        headers.update(extra_headers or {})
        try:
            with httpx.Client(timeout=_timeout()) as client:
                response = client.request(method, f"{base}{path}", json=json_body, headers=headers)
        except httpx.TimeoutException as exc:
            raise PayPalServiceError("timeout", "PayPal took too long to respond. Please try again.", 504) from exc
        except httpx.HTTPError as exc:
            raise PayPalServiceError("network_error", "Could not reach PayPal. Check the internet connection.", 502) from exc

        if response.status_code == 401 and attempt == 0:
            continue  # the cached token may have expired: fetch a new one and retry once
        break

    assert response is not None
    if response.status_code >= 400:
        raise _error_from_response(response)

    try:
        return response.json()
    except ValueError as exc:
        raise PayPalServiceError("paypal_error", "PayPal returned an unreadable response.", 502) from exc


def _is_paypal_sandbox_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ("www.sandbox.paypal.com", "sandbox.paypal.com")


# ----------------------------------------------------------------------
# Orders API
# ----------------------------------------------------------------------

def create_order(
    order_number: str,
    amount_usd: Decimal,
    description: str,
    return_url: str,
    cancel_url: str,
) -> Dict[str, str]:
    """Create a PayPal Sandbox order (intent CAPTURE). Returns id, status and approval_url."""
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": order_number,
                "custom_id": order_number,
                "description": description[:127],
                "amount": {"currency_code": "USD", "value": format(amount_usd, ".2f")},
            }
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "brand_name": "CartPilot AI (Sandbox demo)",
                    "landing_page": "LOGIN",
                    "user_action": "PAY_NOW",
                    "shipping_preference": "NO_SHIPPING",
                    "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                }
            }
        },
    }
    data = _request(
        "POST",
        "/v2/checkout/orders",
        json_body=payload,
        extra_headers={"PayPal-Request-Id": order_number},  # idempotency key
    )

    order_id = data.get("id")
    if not isinstance(order_id, str) or not _ORDER_ID_RE.match(order_id):
        raise PayPalServiceError("paypal_error", "PayPal returned an unexpected order ID.", 502)

    approval_url = None
    for link in data.get("links") or []:
        if isinstance(link, dict) and link.get("rel") in ("payer-action", "approve"):
            approval_url = link.get("href")
            break
    if not approval_url or not _is_paypal_sandbox_url(approval_url):
        raise PayPalServiceError("no_approval_url", "PayPal did not return a valid approval link.", 502)

    return {"id": order_id, "status": str(data.get("status", "")), "approval_url": approval_url}


def capture_order(paypal_order_id: str, request_id: str) -> Dict[str, Any]:
    """Capture an approved order. request_id makes the call idempotent at PayPal."""
    return _request(
        "POST",
        f"/v2/checkout/orders/{paypal_order_id}/capture",
        json_body={},
        extra_headers={"PayPal-Request-Id": request_id, "Prefer": "return=representation"},
    )


def get_order(paypal_order_id: str) -> Dict[str, Any]:
    """Fetch the full order (used when an order was already captured)."""
    return _request("GET", f"/v2/checkout/orders/{paypal_order_id}")