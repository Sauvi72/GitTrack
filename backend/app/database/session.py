from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

db_url = settings.DATABASE_URL
# Render PostgreSQL URLs start with postgres:// or postgresql://
# If no specific driver is specified, route to psycopg2 which is installed
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Ensure SSL mode for cloud PostgreSQL (e.g. Render) if not already specified
if db_url.startswith("postgresql") and "sslmode=" not in db_url and "localhost" not in db_url and "127.0.0.1" not in db_url:
    delimiter = "&" if "?" in db_url else "?"
    db_url = f"{db_url}{delimiter}sslmode=require"

# SQLite connection args require check_same_thread=False for FastAPI concurrency
connect_args = {}
engine_kwargs: dict = {"echo": False, "future": True}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    """Dependency that provides an active database session and ensures cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
