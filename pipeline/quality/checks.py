"""Data quality checks used by the pipeline and dashboard."""

from datetime import datetime, timezone
from typing import Any

import pandas as pd

EXPECTED_CHANNELS = {"Card", "Mobile App", "Web", "API", "ATM"}
SEVERITY_PENALTY = {"Critical": 20, "High": 10, "Medium": 5, "Low": 2}


def _check(
    check_id: str,
    table_name: str,
    check_name: str,
    severity: str,
    observed_value: float,
    passed: bool,
    details: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "table_name": table_name,
        "check_name": check_name,
        "severity": severity,
        "status": "Pass" if passed else "Fail",
        "observed_value": round(float(observed_value), 6),
        "details": details,
        "checked_at": datetime.now(timezone.utc),
    }


def run_quality_checks(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, Any]]:
    customers = tables["customers"]
    accounts = tables["accounts"]
    transactions = tables["transactions"]
    beneficiaries = tables["beneficiaries"]
    checks: list[dict[str, Any]] = []
    check_number = 1

    def add(*args):
        nonlocal check_number
        checks.append(_check(f"DQ{check_number:03d}", *args))
        check_number += 1

    duplicate_count = int(transactions["transaction_id"].duplicated().sum())
    add("transactions", "Duplicate transaction IDs", "Critical", duplicate_count, duplicate_count == 0, f"Found {duplicate_count} duplicates.")
    invalid_amounts = int((transactions["amount"] <= 0).sum())
    add("transactions", "Invalid amounts", "Critical", invalid_amounts, invalid_amounts == 0, f"Found {invalid_amounts} non-positive amounts.")
    negative_balances = int(((transactions["balance_before"] < 0) | (transactions["balance_after"] < 0)).sum())
    add("transactions", "Negative balances", "High", negative_balances, negative_balances == 0, f"Found {negative_balances} negative balance values.")
    missing_customer_ids = int(transactions["sender_customer_id"].isna().sum())
    add("transactions", "Missing customer IDs", "Critical", missing_customer_ids, missing_customer_ids == 0, f"Found {missing_customer_ids} missing customer IDs.")
    invalid_timestamps = int(pd.to_datetime(transactions["timestamp"], errors="coerce", utc=True).isna().sum())
    add("transactions", "Invalid timestamps", "High", invalid_timestamps, invalid_timestamps == 0, f"Found {invalid_timestamps} invalid timestamps.")
    unknown_channels = int((~transactions["channel"].isin(EXPECTED_CHANNELS)).sum())
    add("transactions", "Unknown channels", "Medium", unknown_channels, unknown_channels == 0, f"Found {unknown_channels} unknown channels.")
    known_currencies = set(accounts["currency"].dropna())
    inconsistent_currencies = int((~transactions["currency"].isin(known_currencies)).sum())
    add("transactions", "Inconsistent currencies", "Medium", inconsistent_currencies, inconsistent_currencies == 0, f"Found {inconsistent_currencies} currencies not present in accounts.")
    customer_set = set(customers["customer_id"])
    orphan_transactions = int((~transactions["sender_customer_id"].isin(customer_set)).sum())
    add("transactions", "Orphan transactions", "Critical", orphan_transactions, orphan_transactions == 0, f"Found {orphan_transactions} transactions without a customer.")
    null_rates = []
    for table_name, frame in tables.items():
        required = [column for column in frame.columns if not column.endswith("_json")]
        null_rate = float(frame[required].isna().mean().mean() * 100) if required else 0.0
        null_rates.append((table_name, null_rate))
    worst_table, worst_null_rate = max(null_rates, key=lambda item: item[1])
    add("all tables", "Null percentage", "High", worst_null_rate, worst_null_rate == 0, f"Worst table is {worst_table} at {worst_null_rate:.3f}% nulls.")
    duplicate_customer_ids = int(customers["customer_id"].duplicated().sum())
    add("customers", "Duplicate customer IDs", "High", duplicate_customer_ids, duplicate_customer_ids == 0, f"Found {duplicate_customer_ids} duplicates.")
    orphan_accounts = int((~accounts["customer_id"].isin(customer_set)).sum())
    add("accounts", "Orphan accounts", "Critical", orphan_accounts, orphan_accounts == 0, f"Found {orphan_accounts} accounts without a customer.")
    beneficiary_set = set(beneficiaries["beneficiary_id"])
    missing_beneficiaries = int((~transactions["beneficiary_id"].isin(beneficiary_set)).sum())
    add("transactions", "Missing beneficiary references", "High", missing_beneficiaries, missing_beneficiaries == 0, f"Found {missing_beneficiaries} missing beneficiaries.")
    latest_timestamp = pd.to_datetime(transactions["timestamp"], utc=True).max()
    period_days = int((latest_timestamp - pd.to_datetime(transactions["timestamp"], utc=True).min()).days) + 1
    add("transactions", "Data period coverage", "Low", period_days, period_days >= 90, f"Synthetic transaction period covers {period_days} days.")

    frame = pd.DataFrame(checks)
    failed = frame[frame["status"] == "Fail"]
    penalty = int(sum(SEVERITY_PENALTY.get(severity, 0) for severity in failed["severity"]))
    score = max(0, 100 - penalty)
    quality = {
        "quality_score": score,
        "checks_passed": int((frame["status"] == "Pass").sum()),
        "checks_failed": int((frame["status"] == "Fail").sum()),
        "row_counts": {table: int(len(value)) for table, value in tables.items()},
        "composition": {
            "base_score": 100,
            "penalty_by_severity": SEVERITY_PENALTY,
            "applied_penalty": penalty,
        },
        "issues": failed.to_dict("records"),
        "data_freshness": {
            "latest_event": latest_timestamp.isoformat(),
            "event_period_days": period_days,
            "note": "Freshness is measured against the generated event period, not wall-clock time.",
        },
    }
    return frame, quality
