"""
Database infrastructure with connection pooling and proper error handling.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator, Optional
import structlog
from ..core.exceptions import DatabaseError
from .config import DatabaseConfig

logger = structlog.get_logger(__name__)

Base = declarative_base()


class DatabaseManager:
    """Production-ready database manager with connection pooling."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine = None
        self._session_factory = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with proper configuration."""
        try:
            self._engine = create_engine(
                self.config.get_connection_string(),
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=False  # Set to True for SQL debugging in development
            )
            
            self._session_factory = sessionmaker(bind=self._engine)
            logger.info("Database engine initialized", 
                       host=self.config.host, 
                       database=self.config.database)
            
        except Exception as e:
            logger.error("Failed to initialize database engine", error=str(e))
            raise DatabaseError(f"Database initialization failed: {e}")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with proper cleanup."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Database session error", error=str(e))
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    def create_tables(self):
        """Create all tables defined in models."""
        try:
            Base.metadata.create_all(self._engine)
            logger.info("Database tables created")
        except Exception as e:
            logger.error("Failed to create tables", error=str(e))
            raise DatabaseError(f"Table creation failed: {e}")
    
    def close(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")


class DatabaseSession:
    """Context manager for database operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session: Optional[Session] = None
    
    def __enter__(self) -> Session:
        self.session = self.db_manager._session_factory()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()