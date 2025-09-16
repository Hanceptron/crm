"""
Database connection manager for the Aviation Workflow System.

Provides SQLModel engine initialization, session management, and FastAPI dependencies.
Supports both SQLite (MVP) and PostgreSQL (production) databases.
"""

from typing import Generator, Optional
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event
from sqlalchemy.engine import Engine
from core.config import settings


class DatabaseManager:
    """
    Database connection manager.
    
    Handles engine initialization, session creation, and database setup.
    Provides thread-safe database operations and connection pooling.
    """
    
    def __init__(self):
        """Initialize database manager with engine configuration."""
        self._engine: Optional[Engine] = None
        self._initialized = False
    
    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    def _create_engine(self) -> Engine:
        """
        Create database engine based on configuration.
        
        Returns:
            SQLAlchemy Engine instance configured for the database type
        """
        connect_args = {}
        
        if settings.is_sqlite:
            # SQLite-specific configuration
            connect_args = {
                "check_same_thread": False,  # Allow multiple threads
                "timeout": 20,  # Connection timeout in seconds
            }
            
            # Enable foreign keys for SQLite
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                if "sqlite" in str(dbapi_connection):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                    cursor.execute("PRAGMA synchronous=NORMAL")  # Better performance
                    cursor.close()
        
        elif settings.is_postgresql:
            # PostgreSQL-specific configuration
            connect_args = {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600,  # Recycle connections after 1 hour
                "pool_pre_ping": True,  # Validate connections
            }
        
        # Create engine with appropriate settings
        engine = create_engine(
            settings.database_url,
            connect_args=connect_args,
            echo=settings.debug and settings.is_development,  # Log SQL in debug mode
        )
        
        return engine
    
    def create_db_and_tables(self) -> None:
        """
        Create database and all tables.
        
        Should be called once during application startup to ensure
        all tables exist. Uses SQLModel.metadata.create_all().
        """
        if not self._initialized:
            SQLModel.metadata.create_all(self.engine)
            self._initialized = True
    
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session for dependency injection.
        
        Yields:
            Database session that automatically closes after use
            
        Usage:
            @app.get("/items")
            async def get_items(session: Session = Depends(get_session)):
                return session.exec(select(WorkItem)).all()
        """
        with Session(self.engine) as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    def create_session(self) -> Session:
        """
        Create a new database session.
        
        Returns:
            New database session (must be closed manually)
            
        Note:
            Prefer get_session() for FastAPI dependency injection.
            This method is for use cases where manual session management is needed.
        """
        return Session(self.engine)
    
    def health_check(self) -> bool:
        """
        Check database connectivity.
        
        Returns:
            True if database is accessible, False otherwise
        """
        try:
            with Session(self.engine) as session:
                session.exec("SELECT 1")
                return True
        except Exception:
            return False
    
    def close(self) -> None:
        """Close database engine and all connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._initialized = False


# Global database manager instance
db_manager = DatabaseManager()

# FastAPI dependency for database sessions
def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(session: Session = Depends(get_session)):
            return session.exec(select(WorkItem)).all()
    """
    yield from db_manager.get_session()


def init_db() -> None:
    """
    Initialize database on application startup.
    
    Creates all tables and performs any necessary setup.
    Should be called once during application initialization.
    """
    db_manager.create_db_and_tables()