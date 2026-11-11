"""
Order tables: a safe record of every checkout attempt and its PayPal result.

Money is stored as whole numbers (paise for INR, cents for USD) so that SQLite
never rounds it. Order items are a snapshot, so later price changes in the
products table do not change past orders.

Order status values:
  CREATING        saved locally, PayPal order not created yet
  PENDING         PayPal order created, waiting for the customer to approve
  CAPTURING       a capture request is in progress
  PAID            capture verified: COMPLETED, USD, exact amount  (the ONLY paid state)
  PAYMENT_PENDING PayPal is still processing the payment (not paid)
  FAILED          payment failed or PayPal order could not be created
  CANCELLED       customer cancelled at PayPal
  NEEDS_REVIEW    PayPal reported a capture we could not verify (not marked paid)
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow() -> datetime:
    """Current UTC time without tzinfo (what SQLite stores)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(40), unique=True, index=True, nullable=False)
    # Random secret returned only to the browser that started this checkout.
    checkout_token = Column(String(64), nullable=False)

    paypal_order_id = Column(String(64), unique=True, index=True, nullable=True)
    paypal_capture_id = Column(String(64), nullable=True)
    paypal_capture_status = Column(String(30), nullable=True)

    status = Column(String(20), nullable=False, default="CREATING", index=True)
    status_reason = Column(String(300), nullable=True)

    total_inr_paise = Column(Integer, nullable=False)      # original INR total x 100
    inr_per_usd = Column(String(20), nullable=False)       # demo rate used, e.g. "85"
    total_usd_cents = Column(Integer, nullable=False)      # USD amount sent to PayPal x 100
    currency = Column(String(3), nullable=False, default="USD")

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow)
    captured_at = Column(DateTime, nullable=True)

    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, nullable=False)           # plain number: the snapshot outlives the product row
    product_name = Column(String(200), nullable=False)
    unit_price_paise = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")