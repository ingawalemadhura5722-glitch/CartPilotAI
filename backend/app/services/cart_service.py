"""
Cart validation: never trust prices or quantities sent by the browser.
We re-check every item against the database.
"""

from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.schemas import CartItemIn, CartLineResult, CartValidateResponse


def validate_cart(db: Session, items: List[CartItemIn]) -> CartValidateResponse:
    # If the same product appears twice, merge the quantities into one line.
    merged: Dict[int, Dict[str, float]] = {}
    for item in items:
        if item.product_id in merged:
            merged[item.product_id]["quantity"] += item.quantity
        else:
            merged[item.product_id] = {"quantity": item.quantity, "price": item.price}

    # One database query for all products in the cart.
    products = db.query(Product).filter(Product.id.in_(list(merged.keys()))).all()
    products_by_id = {p.id: p for p in products}

    lines: List[CartLineResult] = []
    subtotal = 0.0

    for product_id, data in merged.items():
        quantity = int(data["quantity"])
        client_price = float(data["price"])
        product = products_by_id.get(product_id)
        issues: List[str] = []

        if product is None:
            lines.append(CartLineResult(
                product_id=product_id, name=None, quantity=quantity,
                client_price=client_price, server_price=None, available_stock=None,
                line_total=0.0, valid=False,
                issues=["Product not found. It may have been removed."],
            ))
            continue

        if product.stock <= 0:
            issues.append("Out of stock.")
        elif quantity > product.stock:
            issues.append(f"Only {product.stock} unit(s) available, but {quantity} requested.")

        if abs(product.price - client_price) > 0.01:
            issues.append(f"Price changed: cart shows {client_price:.2f}, current price is {product.price:.2f}.")

        line_total = round(product.price * quantity, 2)
        subtotal += line_total

        lines.append(CartLineResult(
            product_id=product.id, name=product.name, quantity=quantity,
            client_price=client_price, server_price=product.price,
            available_stock=product.stock, line_total=line_total,
            valid=len(issues) == 0, issues=issues,
        ))

    all_valid = all(line.valid for line in lines)
    subtotal = round(subtotal, 2)

    return CartValidateResponse(
        valid=all_valid,
        items=lines,
        subtotal=subtotal,
        total=subtotal,  # Day 1: no tax or shipping, so total equals subtotal
        message="Cart is valid." if all_valid else "Some items need attention.",
    )