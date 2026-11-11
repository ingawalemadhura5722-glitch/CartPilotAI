# Importing the models here makes sure SQLAlchemy knows about every table
# before main.py calls Base.metadata.create_all().
from app.models.product import Product
from app.models.order import Order, OrderItem

__all__ = ["Product", "Order", "OrderItem"]