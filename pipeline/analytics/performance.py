"""Rule performance and version comparison metrics."""

from typing import Any

import pandas as pd


def build_rule_performance(
    evaluations: dict[str, Any],
    transactions: pd.DataFrame,
    *,
    analyst_minutes: int = 8,
) -> dict[str, Any]:
    tx = transactions[["transaction_id", "is_fraud", "amount"]].copy()
    tx["is_fraud"] = tx["is_fraud"].astype(bool)
    total_fraud = int(tx["is_fraud"].sum())
    rows: list[dict[str, Any]] = []
    for version, evaluation in evaluations.items():
        definitions = {item["rule_id"]: item for item in evaluation.definitions}
        for rule_id, definition in definitions.items():
            results = evaluation.results[evaluation.results["rule_id"] == rule_id]
            merged = results.merge(tx, on="transaction_id", how="left")
            triggered_count = len(merged)
            confirmed = int(merged["is_fraud"].sum()) if triggered_count else 0
            false_positives = triggered_count - confirmed
            precision = confirmed / triggered_count if triggered_count else 0.0
            recall = confirmed / total_fraud if total_fraud else 0.0
            loss_detected = float(merged.loc[merged["is_fraud"], "amount"].sum()) if triggered_count else 0.0
            if precision >= 0.35 and recall >= 0.15:
                recommendation = "keep"
            elif precision < 0.08 and triggered_count > max(10, len(tx) * 0.02):
                recommendation = "tune"
            elif recall < 0.05 and precision >= 0.15:
                recommendation = "segment"
            else:
                recommendation = "investigate further"
            rows.append(
                {
                    "version": version,
                    "rule_id": rule_id,
                    "rule_name": definition["rule_name"],
                    "description": definition["description"],
                    "category": definition["category"],
                    "severity": definition["severity"],
                    "alerts_generated": triggered_count,
                    "percentage_of_total_alerts": round(triggered_count / max(len(tx), 1) * 100, 4),
                    "confirmed_fraud": confirmed,
                    "false_positives": false_positives,
                    "precision": round(precision, 6),
                    "recall": round(recall, 6),
                    "average_score_contribution": float(definition["score"]),
                    "estimated_analyst_minutes": triggered_count * analyst_minutes,
                    "estimated_loss_detected": round(loss_detected, 2),
                    "current_status": "Enabled" if definition.get("enabled", True) else "Disabled",
                    "threshold": definition.get(f"threshold_{version.lower()}"),
                    "v1_threshold": definition.get("threshold_v1"),
                    "v2_threshold": definition.get("threshold_v2"),
                    "recommendation": recommendation,
                }
            )
    by_rule: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_rule.setdefault(row["rule_id"], []).append(row)
    for row in rows:
        versions = {item["version"]: item for item in by_rule[row["rule_id"]]}
        current = versions.get("V2", row)
        v1 = versions.get("V1", row)
        row["v1_alerts"] = v1["alerts_generated"]
        row["v2_alerts"] = current["alerts_generated"]
        row["alert_change"] = current["alerts_generated"] - v1["alerts_generated"]
        row["v1_precision"] = v1["precision"]
        row["v2_precision"] = current["precision"]
    current_rows = [row for row in rows if row["version"] == "V2"]
    return {
        "rules": current_rows,
        "versions": rows,
        "pareto": sorted(current_rows, key=lambda row: row["alerts_generated"], reverse=True),
        "methodology": {
            "confirmed_fraud": "Synthetic is_fraud label used for evaluation only.",
            "false_positive": "Alerted transaction with is_fraud=False.",
            "analyst_minutes_per_alert": analyst_minutes,
        },
    }
