"""Orchestration for Phase 1 synthetic data generation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from pipeline.generator.config import GenerationConfig
from pipeline.generator.entities import (
    generate_accounts,
    generate_beneficiaries,
    generate_customers,
    generate_devices,
)
from pipeline.generator.transactions import generate_transactions


@dataclass
class DatasetBundle:
    tables: dict[str, pd.DataFrame]
    summary: dict[str, Any]


def generate_dataset(config: GenerationConfig) -> DatasetBundle:
    """Generate all Phase 1 tables with a deterministic random generator."""

    rng = np.random.default_rng(config.seed)
    customers = generate_customers(config, rng)
    accounts = generate_accounts(config, customers, rng)
    devices, device_links = generate_devices(config, customers, rng)
    beneficiaries = generate_beneficiaries(config, rng)
    transactions = generate_transactions(
        config,
        customers,
        accounts,
        devices,
        device_links,
        beneficiaries,
        rng,
    )

    tables = {
        "customers": customers,
        "accounts": accounts,
        "devices": devices,
        "device_customer_links": device_links,
        "beneficiaries": beneficiaries,
        "transactions": transactions,
    }
    summary = _build_summary(config, tables)
    return DatasetBundle(tables=tables, summary=summary)


def _build_summary(config: GenerationConfig, tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    transactions = tables["transactions"]
    fraud_rate = float(transactions["is_fraud"].mean()) if len(transactions) else 0.0
    timestamp_series = pd.to_datetime(transactions["timestamp"], utc=True)
    scenario_counts = {
        str(key): int(value)
        for key, value in transactions["fraud_scenario"].value_counts().sort_index().items()
    }
    return {
        "seed": config.seed,
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "period_start": timestamp_series.min().isoformat() if len(transactions) else None,
        "period_end": timestamp_series.max().isoformat() if len(transactions) else None,
        "configured_period_days": config.days,
        "configured_fraud_rate_target": config.fraud_rate_target,
        "actual_fraud_rate": round(fraud_rate, 6),
        "row_counts": {table: int(len(frame)) for table, frame in tables.items()},
        "fraud_scenario_counts": scenario_counts,
        "notes": [
            "All records are synthetic and generated for portfolio demonstration.",
            "is_fraud is a synthetic evaluation label and is not used by Phase 1 generation features.",
            "device_customer_links is the authoritative many-to-many relationship for shared devices.",
        ],
    }
