from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import DisconnectionError, OperationalError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure engine with connection pool settings to handle connection issues
# Garantir que o schema 'public' seja usado por padrão
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Validate connections before using them (fixes stale connections)
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_size=5,         # Number of connections to maintain
    max_overflow=10,     # Maximum overflow connections
    echo=False,          # Set to True for SQL query logging
    connect_args={
        "connect_timeout": 10,
        "options": "-c search_path=public"  # Forçar uso do schema public
    }
)

# Add connection pool event listeners to handle disconnections
@event.listens_for(engine, "connect")
def set_connection_settings(dbapi_conn, connection_record):
    """Set connection-level settings - garantir schema public"""
    if hasattr(dbapi_conn, 'cursor'):
        cursor = dbapi_conn.cursor()
        try:
            # Garantir que estamos usando o schema public
            cursor.execute("SET search_path TO public")
            cursor.close()
        except Exception:
            pass  # Ignorar erros em conexões que não suportam isso

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session.
    
    The pool_pre_ping=True setting ensures connections are validated
    before use, automatically handling stale connections.
    """
    db = SessionLocal()
    try:
        yield db
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Database connection error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
