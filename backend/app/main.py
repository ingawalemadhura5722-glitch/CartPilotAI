"""
CartPilot AI backend: FastAPI application entry point.

Run (from the backend folder):
    uvicorn app.main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

# database.py also loads backend/.env, so env variables are ready below.
from app.database import Base, SessionLocal, engine, get_db
from app import models  # noqa: F401  (registers the Product table)
from app.routes import cart, chat, products
from app.services.seed import seed_products


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts: create tables and seed sample data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        added = seed_products(db)
        if added:
            print(f"Seeded {added} sample products.")
    finally:
        db.close()
    yield  # the app runs here; code after this would run on shutdown


app = FastAPI(
    title="CartPilot AI API",
    description="Day 1 foundation: product catalog, demo (rule-based) assistant and cart validation.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: lets the React app (running on another port) call this API.
origins = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the route groups.
app.include_router(products.router)
app.include_router(chat.router)
app.include_router(cart.router)


@app.get("/", tags=["General"])
def root():
    return {
        "message": "Welcome to the CartPilot AI API",
        "docs": "/docs",
        "stage": "Day 1 foundation (demo assistant, no real AI or payments yet)",
    }


@app.get("/health", tags=["General"])
def health(db: Session = Depends(get_db)):
    """Health check: also confirms the database connection works."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}