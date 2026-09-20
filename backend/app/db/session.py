"""Database engine and session helpers.

SQLite is the local default. The same SQLAlchemy URL can be replaced with a
PostgreSQL URL for deployment without changing repository or service code.
"""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings


def _prepare_sqlite_path(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix) or database_url == "sqlite:///:memory:":
        return
    raw_path = database_url.removeprefix(prefix)
    if raw_path.startswith("/"):
        path = Path(raw_path)
    else:
        path = Path.cwd() / raw_path
    path.parent.mkdir(parents=True, exist_ok=True)


_prepare_sqlite_path(settings.database_url)
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    """Yield one request-scoped SQLAlchemy session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
