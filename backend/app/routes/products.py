"""Product and category endpoints."""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.models.schemas import ProductOut

router = APIRouter(prefix="/api", tags=["Products"])


@router.get("/products", response_model=List[ProductOut])
def list_products(
    q: Optional[str] = Query(None, description="Search words (name, description or category)"),
    category: Optional[str] = Query(None, description="Filter by category, e.g. Laptops"),
    sort: Literal["default", "price_asc", "price_desc", "rating"] = Query("default"),
    db: Session = Depends(get_db),
):
    """Return all products. Supports optional search, category filter and sorting."""
    query = db.query(Product)

    if category and category.lower() != "all":
        query = query.filter(Product.category.ilike(category))

    if q:
        # Every search word must appear in the name, description or category.
        for term in q.split():
            like = f"%{term}%"
            query = query.filter(
                or_(
                    Product.name.ilike(like),
                    Product.description.ilike(like),
                    Product.category.ilike(like),
                )
            )

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "rating":
        query = query.order_by(Product.rating.desc())
    else:
        query = query.order_by(Product.id.asc())

    return query.all()


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Return one product, or a 404 error if it does not exist."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    """Return the distinct product categories."""
    rows = db.query(Product.category).distinct().order_by(Product.category).all()
    return [row[0] for row in rows]