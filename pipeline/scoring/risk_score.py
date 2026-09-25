"""Transparent composite risk score and alert builder."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from pipeline.rules.engine import RuleEvaluation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCORE_CONFIG = PROJECT_ROOT / "pipeline" / "config" / "risk_scoring.yml"


def load_score_config(path: str | Path = DEFAULT_SCORE_CONFIG) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def risk_level(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def _normalise_series(series: pd.Series, upper: float = 100.0) -> pd.Series:
    return series.astype(float).clip(lower=0, upper=upper).fillna(0.0)


def score_transactions(
    transactions: pd.DataFrame,
    features: pd.DataFrame,
    customers: pd.DataFrame,
    devices: pd.DataFrame,
    rule_evaluation: RuleEvaluation,
    *,
    ml_signals: pd.DataFrame | None = None,
    config_path: str | Path = DEFAULT_SCORE_CONFIG,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return transaction scores and a normalized score-component table."""

    config = load_score_config(config_path)
    weights = config.get("weights", {})
    customer_scores = config.get("customer_scores", {"Low": 10, "Medium": 45, "High": 80})
    frame = transactions.merge(features, on="transaction_id", how="inner")
    frame = frame.merge(
        customers[["customer_id", "customer_risk_level", "customer_type"]].rename(
            columns={"customer_id": "sender_customer_id"}
        ),
        on="sender_customer_id",
        how="left",
    )
    frame = frame.merge(
        devices[["device_id", "device_risk_score"]], on="device_id", how="left"
    )
    rule_matrix = rule_evaluation.triggered_matrix[
        ["transaction_id", "rule_score", "triggered_rule_ids"]
    ]
    frame = frame.merge(rule_matrix, on="transaction_id", how="left")
    if ml_signals is not None and not ml_signals.empty:
        frame = frame.merge(ml_signals, on="transaction_id", how="left")
    frame["logistic_probability"] = frame.get("logistic_probability", 0.0)
    frame["anomaly_score"] = frame.get("anomaly_score", 0.0)
    frame[["logistic_probability", "anomaly_score"]] = frame[
        ["logistic_probability", "anomaly_score"]
    ].fillna(0.0)

    unusual_amount = _normalise_series(frame["amount_vs_customer_average"] - 1.0) * 18
    unusual_z = _normalise_series(frame["amount_z_score"].abs(), 8) * 7
    velocity = _normalise_series(frame["transactions_last_1_hour"], 12) * 5
    novelty = (
        frame["is_new_beneficiary"].astype(float) * 12
        + frame["is_new_device"].astype(float) * 12
        + frame["is_new_country"].astype(float) * 8
    )
    depletion = frame["balance_depletion_ratio"].astype(float) * 20
    behavioral_signal = _normalise_series(
        unusual_amount + unusual_z + velocity + novelty + depletion
    )
    anomaly = _normalise_series(frame["anomaly_score"])
    behavioral_score = _normalise_series(behavioral_signal * 0.70 + anomaly * 0.30)
    customer_score = frame["customer_risk_level"].map(customer_scores).fillna(10.0)
    device_score = _normalise_series(
        frame["device_risk_score"].fillna(0) * 0.65 + frame["shared_device_risk"] * 0.35
    )
    network_score = _normalise_series(
        frame["beneficiary_network_risk"] * 0.65
        + frame["connected_account_count"].clip(0, 10) * 3.5
        + frame["circular_transfer_indicator"].astype(float) * 30
    )
    geo_channel_score = _normalise_series(
        frame["is_high_risk_country"].astype(float) * 45
        + frame["is_high_risk_channel"].astype(float) * 20
        + frame["deviation_from_usual_country"].astype(float) * 20
        + frame["deviation_from_usual_city"].astype(float) * 15
    )

    component_values = {
        "rule_score": _normalise_series(frame["rule_score"]),
        "behavioral_score": behavioral_score,
        "customer_score": _normalise_series(customer_score),
        "device_score": device_score,
        "network_score": network_score,
        "geo_channel_score": geo_channel_score,
    }
    total = pd.Series(0.0, index=frame.index)
    for component_name, values in component_values.items():
        total = total + values * float(weights.get(component_name, 0.0))
    frame["risk_score"] = total.clip(0, 100).round(2)
    frame["risk_level"] = frame["risk_score"].map(risk_level)
    frame["alert_priority"] = frame["risk_level"].map(
        {"Critical": "P1", "High": "P2", "Medium": "P3", "Low": "P4"}
    )

    component_rows: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        for component_name, values in component_values.items():
            raw_value = float(values.loc[index])
            component_rows.append(
                {
                    "transaction_id": row["transaction_id"],
                    "component_name": component_name,
                    "raw_value": round(raw_value, 6),
                    "weighted_contribution": round(
                        raw_value * float(weights.get(component_name, 0.0)), 6
                    ),
                    "explanation": _component_explanation(component_name, row, raw_value),
                }
            )
    components = pd.DataFrame(component_rows)
    return frame, components


def _component_explanation(component: str, row: Any, value: float) -> str:
    if component == "rule_score":
        rules = ", ".join(row["triggered_rule_ids"]) if row["triggered_rule_ids"] else "none"
        return f"Rule evidence from {rules}; normalized contribution base {value:.1f}."
    if component == "behavioral_score":
        return f"Behavioral deviation and anomaly signal normalized to {value:.1f}."
    if component == "customer_score":
        return f"Customer profile risk is {row['customer_risk_level']} ({value:.1f}/100)."
    if component == "device_score":
        return f"Device and shared-device context normalized to {value:.1f}."
    if component == "network_score":
        return f"Beneficiary and connected-account context normalized to {value:.1f}."
    return f"Geographic and channel context normalized to {value:.1f}."


def build_alert_tables(
    scored: pd.DataFrame,
    components: pd.DataFrame,
    *,
    threshold: float = 50.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a prioritized queue without creating synthetic analyst decisions.

    The default threshold deliberately reduces the manual queue relative to all
    low/medium risk events. Analysts can still inspect every transaction and
    use the rule tuning simulation to test a different threshold.
    """

    should_alert = scored["risk_score"] >= threshold
    alerts_source = scored.loc[should_alert].sort_values(
        ["risk_score", "timestamp"], ascending=[False, True]
    )
    alert_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    for alert_number, (_, row) in enumerate(alerts_source.iterrows(), start=1):
        alert_id = f"ALR{alert_number:06d}"
        triggered_rule_ids = row["triggered_rule_ids"] or []
        alert_rows.append(
            {
                "alert_id": alert_id,
                "transaction_id": row["transaction_id"],
                "customer_id": row["sender_customer_id"],
                "created_at": row["timestamp"],
                "alert_status": "New",
                "alert_priority": row["alert_priority"],
                "risk_score": float(row["risk_score"]),
                "risk_level": row["risk_level"],
                "triggered_rules_json": json.dumps(triggered_rule_ids),
                "analyst_id": None,
                "assigned_at": None,
                "closed_at": None,
                "disposition": None,
                "investigation_notes": None,
            }
        )
        matching = components[components["transaction_id"] == row["transaction_id"]]
        for component in matching.to_dict("records"):
            component_rows.append(
                {
                    "alert_id": alert_id,
                    "component_name": component["component_name"],
                    "raw_value": component["raw_value"],
                    "weighted_contribution": component["weighted_contribution"],
                    "explanation": component["explanation"],
                }
            )
    alerts = pd.DataFrame(alert_rows)
    alert_components = pd.DataFrame(component_rows)
    return alerts, alert_components
