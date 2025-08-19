"""
Database session dependency for FastAPI.
Provides a scoped SQLAlchemy session that is closed after use.
"""

from app.db import SessionLocal


def get_db():
    """
    Dependency function to get a database session.

    Yields:
        Session: SQLAlchemy session object.

    Ensures:
        The session is closed after the request is completed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
