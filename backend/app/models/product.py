"""The Product table (database model)."""

from sqlalchemy import Column, Float, Integer, String, Text

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)          # price in Indian Rupees (INR)
    rating = Column(Float, nullable=False, default=0.0)   # 0.0 - 5.0
    image_url = Column(String(500), nullable=False)
    stock = Column(Integer, nullable=False, default=0)    # units available