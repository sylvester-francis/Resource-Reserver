# app/database.py
"""Database configuration and session management for the Resource Reserver application.

This module provides the core database connectivity layer using SQLAlchemy ORM.
It handles database engine creation, session management, and provides a
dependency injection function for use with FastAPI endpoints.

Features:
    - Automatic database URL configuration via environment variables
    - SQLite and PostgreSQL support with appropriate connection settings
    - Thread-safe session management with proper cleanup
    - Debug mode SQL logging when DEBUG environment variable is enabled
    - FastAPI-compatible dependency injection for database sessions

Example Usage:
    Using the database session in a FastAPI endpoint::

        from fastapi import Depends
        from sqlalchemy.orm import Session
        from app.database import get_db

        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Direct session usage (for scripts or CLI)::

        from app.database import SessionLocal

        db = SessionLocal()
        try:
            # Perform database operations
            items = db.query(Item).all()
        finally:
            db.close()

Environment Variables:
    DATABASE_URL: Database connection string. Defaults to "sqlite:///./data/db/resource_reserver_dev.db".
        Examples:
            - SQLite: "sqlite:///./data/db/resource_reserver_dev.db"
            - PostgreSQL: "postgresql://user:pass@localhost/dbname"
    DEBUG: When set to "true" (case-insensitive), enables SQL query echo logging.

Author:
    Resource Reserver Development Team
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/db/resource_reserver_dev.db")

db_url = make_url(DATABASE_URL)
if db_url.drivername.startswith("sqlite") and db_url.database and db_url.database != ":memory:":
    db_path = Path(db_url.database)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

# Configure engine with appropriate settings
# SQLite requires check_same_thread=False for FastAPI's async handling
engine = create_engine(
    DATABASE_URL,
    connect_args=({"check_same_thread": False} if "sqlite" in DATABASE_URL else {}),  # noqa : E501
    echo=os.getenv("DEBUG", "false").lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Provide a database session dependency for FastAPI endpoints.

    This generator function creates a new SQLAlchemy session for each request
    and ensures proper cleanup after the request completes, regardless of
    whether the request succeeded or raised an exception.

    Yields:
        sqlalchemy.orm.Session: A SQLAlchemy session instance bound to the
            configured database engine. The session is configured with
            autocommit=False and autoflush=False for explicit transaction
            control.

    Example:
        Use as a FastAPI dependency::

            from fastapi import Depends
            from sqlalchemy.orm import Session

            @app.get("/users/{user_id}")
            def get_user(user_id: int, db: Session = Depends(get_db)):
                return db.query(User).filter(User.id == user_id).first()

    Note:
        The session is automatically closed in the finally block, ensuring
        database connections are properly released back to the connection
        pool even if an exception occurs during request processing.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
