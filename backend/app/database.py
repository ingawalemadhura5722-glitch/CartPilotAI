"""
Database setup (SQLite + SQLAlchemy).

- engine:        the connection to the database file
- SessionLocal:  a factory that creates database sessions
- Base:          the parent class all our table models inherit from
- get_db():      a FastAPI "dependency" that gives each request its own session
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# backend/ folder (two levels up from this file: app/database.py -> backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from backend/.env (if the file exists).
load_dotenv(BASE_DIR / ".env")

# Default: a SQLite file inside the backend folder.
# .as_posix() keeps the path format SQLAlchemy expects, even on Windows.
DEFAULT_DB_URL = f"sqlite:///{(BASE_DIR / 'cartpilot.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# check_same_thread=False is needed for SQLite because FastAPI may use
# different threads to handle requests.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    """Open a database session for one request, then always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()