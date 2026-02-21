# =============================================================
#  database.py — SQLAlchemy Engine + Session + Base setup
# =============================================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./procurement.db")

# connect_args is required for SQLite to allow multi-thread usage with FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Each request gets its own session, closed after the request finishes
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# All models inherit from this Base — SQLAlchemy uses it to track table definitions
Base = declarative_base()


def get_db():
    """
    FastAPI dependency — yields a DB session per request.
    Guarantees the session is always closed, even if an error occurs.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
