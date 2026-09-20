"""Configuration-driven explainable rules R001-R012."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULE_CONFIG = PROJECT_ROOT / "pipeline" / "config" / "rules.yml"


@dataclass
class RuleEvaluation:
    version: str
    results: pd.DataFrame
    triggered_matrix: pd.DataFrame
    rule_score: pd.Series
    definitions: list[dict[str, Any]]


def load_rule_definitions(path: str | Path = DEFAULT_RULE_CONFIG) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    return payload.get("rules", [])


def _rule_mask(rule_id: str, frame: pd.DataFrame, threshold: Any) -> pd.Series:
    if rule_id == "R001":
        return frame["is_night"]
    if rule_id == "R002":
        return frame["is_new_device"]
    if rule_id == "R003":
        return frame["is_new_beneficiary"]
    if rule_id == "R004":
        return (frame["amount_vs_customer_average"] >= float(threshold)) | (
            frame["amount_z_score"] >= float(threshold)
        )
    if rule_id == "R005":
        threshold_value = int(threshold)
        return (frame["transactions_last_1_hour"] >= threshold_value) | (
            frame["transactions_last_10_minutes"] >= max(3, threshold_value // 2)
        )
    if rule_id == "R006":
        return frame["balance_depletion_ratio"] >= float(threshold)
    if rule_id == "R007":
        return (
            frame["deviation_from_usual_city"]
            | frame["deviation_from_usual_country"]
            | frame["is_high_risk_country"]
        )
    if rule_id == "R008":
        return frame["number_of_customers_per_device"] >= int(threshold)
    if rule_id == "R009":
        return frame["number_of_senders_to_beneficiary"] >= int(threshold)
    if rule_id == "R010":
        return frame["customer_risk_level"] == "High"
    if rule_id == "R011":
        return frame["amount"].between(800, 1_000) & (
            frame["transactions_last_1_hour"] >= int(threshold)
        )
    if rule_id == "R012":
        return frame["circular_transfer_indicator"]
    raise ValueError(f"Unknown rule id: {rule_id}")


def _evidence(rule_id: str, row: Any) -> dict[str, Any]:
    fields = {
        "R001": ["transaction_hour", "is_night"],
        "R002": ["is_new_device", "device_id"],
        "R003": ["is_new_beneficiary", "beneficiary_id"],
        "R004": ["amount", "customer_avg_transaction_amount", "amount_vs_customer_average", "amount_z_score"],
        "R005": ["transactions_last_10_minutes", "transactions_last_1_hour"],
        "R006": ["balance_depletion_ratio", "balance_before", "amount"],
        "R007": ["city", "country", "deviation_from_usual_city", "deviation_from_usual_country"],
        "R008": ["device_id", "number_of_customers_per_device", "shared_device_risk"],
        "R009": ["beneficiary_id", "number_of_senders_to_beneficiary", "beneficiary_network_risk"],
        "R010": ["customer_risk_level", "customer_segment"],
        "R011": ["amount", "transactions_last_1_hour"],
        "R012": ["circular_transfer_indicator", "connected_account_count"],
    }
    result: dict[str, Any] = {}
    for field in fields.get(rule_id, []):
        value = getattr(row, field, None)
        if hasattr(value, "item"):
            value = value.item()
        if pd.isna(value) if not isinstance(value, (dict, list, tuple, str, bool)) else False:
            value = None
        result[field] = value
    return result


def _reason(rule_id: str, row: Any) -> str:
    if rule_id == "R001":
        return f"Transaction occurred at {int(row.transaction_hour):02d}:00 during the night monitoring window."
    if rule_id == "R002":
        return "The device was not previously observed for this customer."
    if rule_id == "R003":
        return "The beneficiary was not previously observed for this customer."
    if rule_id == "R004":
        return f"Amount was {float(row.amount_vs_customer_average):.1f}x the customer's prior average."
    if rule_id == "R005":
        return f"Customer had {int(row.transactions_last_1_hour)} transactions in the prior hour."
    if rule_id == "R006":
        return f"Transaction depleted {float(row.balance_depletion_ratio) * 100:.1f}% of available balance."
    if rule_id == "R007":
        return "Transaction geography differs from the customer's prior pattern or uses a high-risk country."
    if rule_id == "R008":
        return f"Device was previously associated with {int(row.number_of_customers_per_device)} customer(s)."
    if rule_id == "R009":
        return f"Beneficiary was previously used by {int(row.number_of_senders_to_beneficiary)} sender(s)."
    if rule_id == "R010":
        return "Customer profile is classified as high risk."
    if rule_id == "R011":
        return "Several transfers are near the structuring threshold in a short time window."
    if rule_id == "R012":
        return "The transaction is connected to a repeated flow across related entities."
    return "Rule triggered."


def evaluate_rules(
    transactions: pd.DataFrame,
    features: pd.DataFrame,
    customers: pd.DataFrame,
    *,
    version: str = "V2",
    config_path: str | Path = DEFAULT_RULE_CONFIG,
) -> RuleEvaluation:
    """Evaluate every configured rule using only pre-computed transaction features."""

    definitions = load_rule_definitions(config_path)
    customer_risk = customers.set_index("customer_id")["customer_risk_level"].to_dict()
    customer_type = customers.set_index("customer_id")["customer_type"].to_dict()
    frame = transactions.merge(features, on="transaction_id", how="inner", suffixes=("", "_feature"))
    frame["customer_risk_level"] = frame["sender_customer_id"].map(customer_risk)
    frame["customer_type"] = frame["sender_customer_id"].map(customer_type)
    frame = frame.sort_values(["timestamp", "transaction_id"]).reset_index(drop=True)

    trigger_columns: dict[str, pd.Series] = {}
    score = pd.Series(0.0, index=frame.index)
    result_rows: list[dict[str, Any]] = []
    for definition in definitions:
        rule_id = str(definition["rule_id"])
        threshold = definition.get(f"threshold_{version.lower()}")
        mask = _rule_mask(rule_id, frame, threshold).fillna(False).astype(bool)
        trigger_columns[rule_id] = mask
        rule_score = float(definition["score"])
        score = score + mask.astype(float) * rule_score
        for row in frame.loc[mask].itertuples(index=False):
            evidence = _evidence(rule_id, row)
            result_rows.append(
                {
                    "rule_result_id": f"{row.transaction_id}-{rule_id}-{version}",
                    "transaction_id": row.transaction_id,
                    "rule_id": rule_id,
                    "rule_name": definition["rule_name"],
                    "rule_category": definition["category"],
                    "triggered": True,
                    "rule_score": rule_score,
                    "rule_reason": _reason(rule_id, row),
                    "evaluated_at": row.timestamp,
                    "rule_version": version,
                    "evidence_json": json.dumps(evidence, default=str),
                }
            )

    matrix = pd.DataFrame({"transaction_id": frame["transaction_id"], **trigger_columns})
    matrix["rule_score"] = score.clip(upper=100.0).round(6)
    matrix["triggered_rule_ids"] = matrix.apply(
        lambda row: [rule_id for rule_id in trigger_columns if bool(row[rule_id])], axis=1
    )
    results = pd.DataFrame(result_rows)
    if results.empty:
        results = pd.DataFrame(
            columns=[
                "rule_result_id",
                "transaction_id",
                "rule_id",
                "rule_name",
                "rule_category",
                "triggered",
                "rule_score",
                "rule_reason",
                "evaluated_at",
                "rule_version",
                "evidence_json",
            ]
        )
    return RuleEvaluation(
        version=version,
        results=results,
        triggered_matrix=matrix,
        rule_score=score.clip(upper=100.0).round(6),
        definitions=definitions,
    )
