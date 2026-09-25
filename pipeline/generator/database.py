"""Persistence helpers for generated data.

The generator writes through SQLAlchemy/pandas so the storage layer remains
replaceable. The local implementation uses SQLite; PostgreSQL can be supplied
through a normal SQLAlchemy DATABASE_URL.
"""

from pathlib import Path
from typing import Mapping

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from backend.app.db.models import Base

TABLE_ORDER = [
    "customers",
    "accounts",
    "devices",
    "device_customer_links",
    "beneficiaries",
    "transactions",
    "transaction_features",
    "rule_definitions",
    "rule_results",
    "alerts",
    "alert_score_components",
    "analysts",
    "cases",
    "model_metrics",
    "data_quality_results",
    "business_insights",
]


def make_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite:///") and database_url != "sqlite:///:memory:":
        raw_path = database_url.removeprefix("sqlite:///")
        path = Path(raw_path if raw_path.startswith("/") else Path.cwd() / raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


def persist_dataset(
    tables: Mapping[str, pd.DataFrame],
    database_url: str,
    *,
    reset: bool = True,
) -> None:
    """Create the schema and append generated entity tables."""

    engine = make_engine(database_url)
    try:
        if reset:
            Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        for table_name in TABLE_ORDER:
            frame = tables.get(table_name)
            if frame is None:
                continue
            frame.to_sql(
                table_name,
                con=engine,
                if_exists="append",
                index=False,
                chunksize=1_000,
                method="multi",
            )
    finally:
        engine.dispose()
