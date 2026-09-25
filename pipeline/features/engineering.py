"""Chronological, leakage-safe transaction feature engineering.

Every row is scored against state accumulated from earlier transactions only.
The synthetic `is_fraud` label is deliberately never read by this module.
"""

from collections import Counter, defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd

from pipeline.generator.entities import HIGH_RISK_COUNTRIES

HIGH_RISK_CHANNELS = {"API", "ATM"}


def _mode(values: list[str], fallback: str) -> str:
    return Counter(values).most_common(1)[0][0] if values else fallback


def _bounded_ratio(value: float, denominator: float) -> float:
    return float(np.clip(value / max(denominator, 1.0), 0.0, 1.0))


def engineer_features(
    transactions: pd.DataFrame,
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    devices: pd.DataFrame,
    device_links: pd.DataFrame,
    beneficiaries: pd.DataFrame,
) -> pd.DataFrame:
    """Build requested transaction, customer and network features chronologically."""

    tx = transactions.copy()
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], utc=True)
    tx = tx.sort_values(["timestamp", "transaction_id"]).reset_index(drop=True)

    customer_lookup = customers.set_index("customer_id").to_dict("index")
    device_lookup = devices.set_index("device_id").to_dict("index")
    beneficiary_lookup = beneficiaries.set_index("beneficiary_id").to_dict("index")
    account_counts = accounts.groupby("customer_id")["account_id"].nunique().to_dict()
    customer_devices_static = device_links.groupby("customer_id")["device_id"].apply(set).to_dict()

    # All state dictionaries contain only transactions already passed in the loop.
    customer_events: dict[str, list[dict]] = defaultdict(list)
    customer_amounts: dict[str, list[float]] = defaultdict(list)
    customer_devices: dict[str, set[str]] = defaultdict(set)
    customer_countries: dict[str, set[str]] = defaultdict(set)
    customer_cities: dict[str, list[str]] = defaultdict(list)
    device_customers: dict[str, set[str]] = defaultdict(set)
    device_accounts: dict[str, set[str]] = defaultdict(set)
    beneficiary_senders: dict[str, set[str]] = defaultdict(set)
    sender_beneficiaries: dict[str, set[str]] = defaultdict(set)

    rows: list[dict] = []
    for transaction in tx.to_dict("records"):
        transaction_id = str(transaction["transaction_id"])
        timestamp = pd.Timestamp(transaction["timestamp"])
        customer_id = str(transaction["sender_customer_id"])
        account_id = str(transaction["sender_account_id"])
        device_id = str(transaction["device_id"])
        beneficiary_id = str(transaction["beneficiary_id"])
        amount = float(transaction["amount"])
        balance_before = float(transaction["balance_before"])
        customer = customer_lookup[customer_id]
        device = device_lookup[device_id]
        beneficiary = beneficiary_lookup[beneficiary_id]
        prior_events = customer_events[customer_id]
        prior_amounts = customer_amounts[customer_id]
        cutoff_10m = timestamp - timedelta(minutes=10)
        cutoff_1h = timestamp - timedelta(hours=1)
        cutoff_24h = timestamp - timedelta(hours=24)
        cutoff_30d = timestamp - timedelta(days=30)
        recent_10m = [event for event in prior_events if event["timestamp"] >= cutoff_10m]
        recent_1h = [event for event in prior_events if event["timestamp"] >= cutoff_1h]
        recent_24h = [event for event in prior_events if event["timestamp"] >= cutoff_24h]
        recent_30d = [event for event in prior_events if event["timestamp"] >= cutoff_30d]

        avg_amount = float(np.mean(prior_amounts)) if prior_amounts else amount
        median_amount = float(np.median(prior_amounts)) if prior_amounts else amount
        std_amount = float(np.std(prior_amounts)) if len(prior_amounts) > 1 else 0.0
        amount_vs_average = amount / max(avg_amount, 1.0)
        amount_z_score = (amount - avg_amount) / std_amount if std_amount > 0 else 0.0
        amount_percentile = (
            float(np.mean(np.asarray(prior_amounts) <= amount)) if prior_amounts else 0.5
        )
        registration_date = pd.Timestamp(customer["registration_date"])
        days_since_registration = max((timestamp.date() - registration_date.date()).days, 0)
        first_prior_timestamp = prior_events[0]["timestamp"] if prior_events else timestamp
        active_days = max((timestamp - first_prior_timestamp).total_seconds() / 86_400, 1.0)
        usual_city = _mode(customer_cities[customer_id], str(customer["city"]))
        usual_country = _mode(
            [event["country"] for event in prior_events], str(device["country"])
        )
        static_customer_devices = customer_devices_static.get(customer_id, set())
        previous_device_seen = device_id in customer_devices[customer_id]
        is_new_device = not previous_device_seen
        is_new_beneficiary = beneficiary_id not in sender_beneficiaries[customer_id]
        is_new_country = str(transaction["country"]) not in customer_countries[customer_id]
        shared_customer_count = len(device_customers[device_id])
        shared_account_count = len(device_accounts[device_id])
        sender_count = len(beneficiary_senders[beneficiary_id])
        beneficiary_risk = str(beneficiary["beneficiary_risk_level"])
        shared_device_risk = min(
            100.0,
            max(shared_customer_count - 1, 0) * 22.0 + float(device["device_risk_score"]) * 0.35,
        )
        beneficiary_network_risk = min(
            100.0,
            sender_count * 10.0 + (35.0 if beneficiary_risk == "High" else 0.0),
        )
        circular_indicator = bool(
            sender_count >= 2
            and shared_customer_count >= 2
            and account_counts.get(customer_id, 1) >= 2
        )
        connected_accounts = max(
            account_counts.get(customer_id, 1),
            shared_account_count,
            len(
                {
                    linked_account
                    for linked_device in static_customer_devices
                    for linked_account in device_accounts[linked_device]
                }
            ),
        )
        if customer["customer_type"] == "small_business":
            customer_segment = "small_business"
        elif customer["customer_risk_level"] == "High":
            customer_segment = "high_risk_customer"
        elif days_since_registration < 90:
            customer_segment = "new_customer"
        elif customer["customer_type"] == "high_value_customer":
            customer_segment = "high_value_customer"
        else:
            customer_segment = "standard_customer"

        rows.append(
            {
                "transaction_id": transaction_id,
                "transaction_hour": int(timestamp.hour),
                "day_of_week": int(timestamp.dayofweek),
                "is_night": bool(1 <= timestamp.hour <= 5),
                "is_weekend": bool(timestamp.dayofweek >= 5),
                "amount_log": float(np.log1p(amount)),
                "amount_percentile": round(amount_percentile, 6),
                "is_new_beneficiary": bool(is_new_beneficiary),
                "is_new_device": bool(is_new_device),
                "is_new_country": bool(is_new_country),
                "is_high_risk_country": bool(str(transaction["country"]) in HIGH_RISK_COUNTRIES),
                "is_high_risk_channel": bool(str(transaction["channel"]) in HIGH_RISK_CHANNELS),
                "balance_depletion_ratio": round(_bounded_ratio(amount, balance_before), 6),
                "customer_avg_transaction_amount": round(avg_amount, 6),
                "customer_median_transaction_amount": round(median_amount, 6),
                "customer_std_transaction_amount": round(std_amount, 6),
                "amount_vs_customer_average": round(amount_vs_average, 6),
                "amount_z_score": round(float(amount_z_score), 6),
                "customer_transaction_frequency": round(len(prior_events) / active_days, 6),
                "customer_days_since_registration": int(days_since_registration),
                "deviation_from_usual_city": bool(str(transaction["city"]) != usual_city),
                "deviation_from_usual_country": bool(str(transaction["country"]) != usual_country),
                "transactions_last_10_minutes": len(recent_10m),
                "transactions_last_1_hour": len(recent_1h),
                "transactions_last_24_hours": len(recent_24h),
                "unique_beneficiaries_last_24_hours": len(
                    {event["beneficiary_id"] for event in recent_24h}
                ),
                "unique_devices_last_30_days": len(
                    {event["device_id"] for event in recent_30d}
                ),
                "number_of_customers_per_device": shared_customer_count,
                "number_of_accounts_per_device": shared_account_count,
                "number_of_senders_to_beneficiary": sender_count,
                "number_of_beneficiaries_from_sender": len(sender_beneficiaries[customer_id]),
                "shared_device_risk": round(shared_device_risk, 6),
                "beneficiary_network_risk": round(beneficiary_network_risk, 6),
                "circular_transfer_indicator": circular_indicator,
                "connected_account_count": int(connected_accounts),
                "customer_segment": customer_segment,
            }
        )

        event = {
            "timestamp": timestamp,
            "beneficiary_id": beneficiary_id,
            "device_id": device_id,
            "country": str(transaction["country"]),
            "city": str(transaction["city"]),
            "account_id": account_id,
        }
        customer_events[customer_id].append(event)
        customer_amounts[customer_id].append(amount)
        customer_devices[customer_id].add(device_id)
        customer_countries[customer_id].add(str(transaction["country"]))
        customer_cities[customer_id].append(str(transaction["city"]))
        device_customers[device_id].add(customer_id)
        device_accounts[device_id].add(account_id)
        beneficiary_senders[beneficiary_id].add(customer_id)
        sender_beneficiaries[customer_id].add(beneficiary_id)

    return pd.DataFrame(rows)
