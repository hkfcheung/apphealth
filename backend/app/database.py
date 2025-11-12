"""Database connection and initialization."""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create engine with proper pooling for SQLite
# StaticPool uses a single connection which is better for SQLite
if "sqlite" in settings.database_url:
    engine = create_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # For other databases, use larger pool
    engine = create_engine(
        settings.database_url,
        echo=False,
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


def init_db():
    """Initialize database tables."""
    logger.info("Initializing database...")
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized successfully")


def get_session():
    """Get database session."""
    with Session(engine) as session:
        yield session
