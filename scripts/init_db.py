"""Create all database tables without loading data."""

from backend.app.db.models import Base
from backend.app.db.session import engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database schema created.")
