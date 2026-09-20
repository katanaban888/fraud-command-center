"""Generate data-driven, clearly labelled analytical insights."""

from datetime import date
from typing import Any

import pandas as pd


def _insight(
    insight_id: str,
    title: str,
    metric: str,
    comparison: str,
    explanation: str,
    implication: str,
    start: date,
    end: date,
) -> dict[str, Any]:
    return {
        "insight_id": insight_id,
        "title": title,
        "metric": metric,
        "comparison": comparison,
        "explanation": explanation,
        "business_implication": implication,
        "period_start": start,
        "period_end": end,
    }


def generate_insights(
    tables: dict[str, pd.DataFrame],
    rule_performance: dict[str, Any],
) -> pd.DataFrame:
    tx = tables["transactions"].copy()
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], utc=True)
    tx["is_fraud"] = tx["is_fraud"].astype(bool)
    customers = tables["customers"]
    features = tables.get("transaction_features", pd.DataFrame())
    joined = tx.merge(
        customers[["customer_id", "customer_type", "region", "customer_risk_level"]],
        left_on="sender_customer_id",
        right_on="customer_id",
        how="left",
    )
    start = tx["timestamp"].min().date()
    end = tx["timestamp"].max().date()
    output: list[dict[str, Any]] = []

    channel_rates = joined.groupby("channel")["is_fraud"].mean().sort_values(ascending=False)
    channel = channel_rates.index[0]
    output.append(
        _insight(
            "INS001",
            "Channel with the highest synthetic fraud rate",
            f"{channel}: {channel_rates.iloc[0] * 100:.2f}%",
            f"Overall fraud rate: {joined['is_fraud'].mean() * 100:.2f}%",
            "Fraud labels are grouped by transaction channel and compared with the overall synthetic rate.",
            "Use channel as a prioritization context, then validate whether controls or customer mix explain the difference.",
            start,
            end,
        )
    )
    segment_alerts = joined.groupby("customer_type")["is_fraud"].sum().sort_values(ascending=False)
    top_segment = segment_alerts.index[0]
    output.append(
        _insight(
            "INS002",
            "Customer segment with the most labelled fraud",
            f"{top_segment}: {int(segment_alerts.iloc[0])} transactions",
            f"Next segment: {int(segment_alerts.iloc[1]) if len(segment_alerts) > 1 else 0}",
            "Counts use the synthetic ground-truth label and are not a production risk conclusion.",
            "Review segment-specific baselines instead of applying one threshold to all customers.",
            start,
            end,
        )
    )
    rule_rows = rule_performance.get("rules", [])
    worst_rule = min(rule_rows, key=lambda row: row["precision"]) if rule_rows else None
    if worst_rule:
        output.append(
            _insight(
                "INS003",
                "Rule with the highest false-positive rate",
                f"{worst_rule['rule_id']} {worst_rule['rule_name']}: {(1 - worst_rule['precision']) * 100:.1f}%",
                f"Triggered {worst_rule['alerts_generated']} times; precision {worst_rule['precision'] * 100:.1f}%",
                "False positives are calculated as alerted transactions without the synthetic fraud label.",
                "This rule is a candidate for tuning, segmentation or combination with another signal.",
                start,
                end,
            )
        )
    region_amount = joined.loc[joined["is_fraud"], :].groupby("region")["amount"].sum().sort_values(ascending=False)
    top_region = region_amount.index[0] if len(region_amount) else "No labelled fraud"
    top_region_amount = float(region_amount.iloc[0]) if len(region_amount) else 0.0
    output.append(
        _insight(
            "INS004",
            "Region with the largest labelled suspicious amount",
            f"{top_region}: ${top_region_amount:,.0f}",
            f"Total labelled suspicious amount: ${joined.loc[joined['is_fraud'], 'amount'].sum():,.0f}",
            "Amounts are summed for synthetic transactions labelled as fraud.",
            "Use regional context for analyst workload planning, not as a standalone adverse-action signal.",
            start,
            end,
        )
    )
    if not features.empty:
        new_device_rate = float(features.loc[features["is_new_device"], "transaction_id"].nunique() / len(features) * 100)
        output.append(_insight("INS005", "Transactions involving new devices", f"{new_device_rate:.1f}% of transactions", "Compared with 100% of the event population", "The feature is computed from prior customer-device history only.", "New-device thresholds should be calibrated by customer tenure and device-sharing context.", start, end))
        night_rate = float(tx.loc[features.set_index("transaction_id").reindex(tx["transaction_id"])["is_night"].fillna(False).to_numpy(), "is_fraud"].mean() * 100) if tx["is_fraud"].any() else 0.0
        output.append(_insight("INS006", "Share of labelled fraud occurring at night", f"{night_rate:.1f}%", f"Overall night share: {features['is_night'].mean() * 100:.1f}%", "Night is defined as 01:00–05:00 UTC in the feature pipeline.", "Night activity can raise review priority but should not automatically block a transaction.", start, end))
        high_velocity = int((features["transactions_last_1_hour"] >= 4).sum())
        output.append(_insight("INS007", "High-velocity activity volume", f"{high_velocity:,} transactions", f"{high_velocity / len(features) * 100:.1f}% of feature rows", "Velocity uses transactions observed before the current event.", "Velocity alerts may benefit from customer-segment thresholds to reduce workload.", start, end))
    else:
        output.extend([
            _insight("INS005", "New-device analysis", "Pending feature pipeline", "No feature table available", "Feature engineering has not been run.", "Run the analytics pipeline before interpreting device signals.", start, end),
            _insight("INS006", "Night activity analysis", "Pending feature pipeline", "No feature table available", "Feature engineering has not been run.", "Run the analytics pipeline before interpreting time signals.", start, end),
            _insight("INS007", "Velocity analysis", "Pending feature pipeline", "No feature table available", "Feature engineering has not been run.", "Run the analytics pipeline before interpreting velocity signals.", start, end),
        ])
    beneficiaries = joined.groupby("beneficiary_id")["sender_customer_id"].nunique().sort_values(ascending=False)
    shared_beneficiaries = int((beneficiaries >= 2).sum())
    output.append(_insight("INS008", "Beneficiaries shared by multiple customers", f"{shared_beneficiaries:,} beneficiaries", f"Top beneficiary connected to {int(beneficiaries.iloc[0]) if len(beneficiaries) else 0} customers", "The metric describes a network relationship and is not proof of coordinated fraud.", "Prioritize connected-entity review when beneficiary concentration and behavioral signals co-occur.", start, end))
    customer_volume = joined.groupby("sender_customer_id")["amount"].sum().sort_values(ascending=False)
    top_n = max(1, int(len(customer_volume) * 0.01))
    share = float(customer_volume.head(top_n).sum() / max(customer_volume.sum(), 1) * 100)
    output.append(_insight("INS009", "Transaction amount share from top 1% of customers", f"{share:.1f}% of total volume", f"Top {top_n} customers of {len(customer_volume)}", "The concentration is calculated from synthetic transaction amounts.", "Use concentration to plan enhanced monitoring while avoiding income-based assumptions without fairness review.", start, end))
    best_rule = max(rule_rows, key=lambda row: (row["precision"] * row["recall"]) ** 0.5) if rule_rows else None
    output.append(_insight("INS010", "Best rule precision-recall balance", f"{best_rule['rule_id']} {best_rule['rule_name']}" if best_rule else "Pending rule evaluation", f"Geometric mean: {(best_rule['precision'] * best_rule['recall']) ** 0.5:.3f}" if best_rule else "No rule results available", "The balance uses the geometric mean so a rule cannot score well by precision or recall alone.", "Keep this as an analytical recommendation and validate with investigator feedback.", start, end))
    return pd.DataFrame(output)
