"""SQLAlchemy database engine, session factory, and Base declarative model."""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Default to the dedicated Tattva PostgreSQL container on port 55432
DEFAULT_DB_URL = "postgresql+psycopg://postgres:postgres@localhost:55432/tattva_film_director"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# Configure engine with reasonable pooling
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI and service dependency for acquiring a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
