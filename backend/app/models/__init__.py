# Importing Product here makes sure SQLAlchemy knows about the table
# before we call Base.metadata.create_all().
from app.models.product import Product

__all__ = ["Product"]