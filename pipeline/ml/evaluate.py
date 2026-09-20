"""Interpretable baseline and anomaly prioritization evaluation."""

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "amount_log",
    "amount_percentile",
    "is_night",
    "is_weekend",
    "is_new_beneficiary",
    "is_new_device",
    "is_new_country",
    "is_high_risk_country",
    "is_high_risk_channel",
    "balance_depletion_ratio",
    "amount_vs_customer_average",
    "amount_z_score",
    "customer_transaction_frequency",
    "customer_days_since_registration",
    "deviation_from_usual_city",
    "deviation_from_usual_country",
    "transactions_last_10_minutes",
    "transactions_last_1_hour",
    "transactions_last_24_hours",
    "unique_beneficiaries_last_24_hours",
    "unique_devices_last_30_days",
    "number_of_customers_per_device",
    "number_of_accounts_per_device",
    "number_of_senders_to_beneficiary",
    "number_of_beneficiaries_from_sender",
    "shared_device_risk",
    "beneficiary_network_risk",
    "circular_transfer_indicator",
    "connected_account_count",
]


def _safe_auc(y_true: np.ndarray, score: np.ndarray, *, average_precision: bool = False) -> float:
    try:
        return float(
            average_precision_score(y_true, score)
            if average_precision
            else roc_auc_score(y_true, score)
        )
    except ValueError:
        return 0.0


def _classification_metrics(
    y_true: np.ndarray,
    score: np.ndarray,
    threshold: float,
    amounts: np.ndarray,
    *,
    minutes_per_alert: int = 8,
    prevention_rate: float = 0.70,
) -> dict[str, Any]:
    predicted = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    alert_count = int(predicted.sum())
    fraud_amount_detected = float(amounts[(y_true == 1) & (predicted == 1)].sum())
    total_fraud_amount = float(amounts[y_true == 1].sum())
    return {
        "alert_volume": alert_count,
        "suspicious_transaction_volume": alert_count,
        "precision": round(float(precision_score(y_true, predicted, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, predicted, zero_division=0)), 6),
        "f1": round(float(f1_score(y_true, predicted, zero_division=0)), 6),
        "false_positive_rate": round(float(fp / max(fp + tn, 1)), 6),
        "average_risk_score": round(float(score[predicted == 1].mean()) if alert_count else 0.0, 4),
        "alerts_per_analyst": round(alert_count / 6, 2),
        "estimated_loss_detected": round(fraud_amount_detected, 2),
        "estimated_prevented_loss": round(fraud_amount_detected * prevention_rate, 2),
        "investigation_workload_minutes": alert_count * minutes_per_alert,
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "total_fraud_amount": round(total_fraud_amount, 2),
    }


def _feature_frame(features: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    frame = features.copy()
    numeric = frame[FEATURE_COLUMNS].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return numeric, FEATURE_COLUMNS


def evaluate_models(
    transactions: pd.DataFrame,
    features: pd.DataFrame,
    rule_score: pd.DataFrame,
    *,
    minutes_per_alert: int = 8,
    prevention_rate: float = 0.70,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    """Fit time-split models and return per-transaction signals plus report artifacts."""

    tx = transactions[["transaction_id", "timestamp", "is_fraud", "amount"]].copy()
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], utc=True)
    tx = tx.sort_values(["timestamp", "transaction_id"]).reset_index(drop=True)
    feature_frame = features.merge(tx[["transaction_id"]], on="transaction_id", how="right")
    X, feature_names = _feature_frame(feature_frame)
    y = tx["is_fraud"].astype(int).to_numpy()
    split_index = max(1, int(len(tx) * 0.75))
    train_mask = np.arange(len(tx)) < split_index
    test_mask = ~train_mask
    if len(np.unique(y[train_mask])) < 2:
        train_mask = np.ones(len(tx), dtype=bool)
        test_mask = np.zeros(len(tx), dtype=bool)
    logistic = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=500,
                    random_state=random_state,
                ),
            ),
        ]
    )
    logistic.fit(X.loc[train_mask], y[train_mask])
    logistic_probability = logistic.predict_proba(X)[:, 1]

    isolation = IsolationForest(
        n_estimators=120,
        contamination="auto",
        random_state=random_state,
        n_jobs=-1,
    )
    isolation.fit(X.loc[train_mask])
    anomaly_raw = -isolation.decision_function(X)
    anomaly_score = pd.Series(anomaly_raw).rank(pct=True).to_numpy() * 100

    rule_signal = rule_score.set_index("transaction_id").reindex(tx["transaction_id"])["rule_score"].fillna(0).to_numpy()
    rule_signal = np.clip(rule_signal, 0, 100)
    approaches = {
        "rules-only": rule_signal,
        "rules + Isolation Forest": rule_signal * 0.75 + anomaly_score * 0.25,
        "rules + Logistic Regression": rule_signal * 0.75 + logistic_probability * 25,
        "rules + combined score": rule_signal * 0.60 + anomaly_score * 0.20 + logistic_probability * 20,
    }
    thresholds = {
        "rules-only": 18.0,
        "rules + Isolation Forest": 60.0,
        "rules + Logistic Regression": 60.0,
        "rules + combined score": 60.0,
    }

    metrics: dict[str, dict[str, Any]] = {}
    model_metric_rows: list[dict[str, Any]] = []
    amounts = tx["amount"].astype(float).to_numpy()
    metric_row_number = 1
    for approach, score in approaches.items():
        report = _classification_metrics(
            y,
            score,
            thresholds[approach],
            amounts,
            minutes_per_alert=minutes_per_alert,
            prevention_rate=prevention_rate,
        )
        report["roc_auc"] = round(_safe_auc(y, score), 6)
        report["pr_auc"] = round(_safe_auc(y, score, average_precision=True), 6)
        report["threshold"] = thresholds[approach]
        report["train_rows"] = int(train_mask.sum())
        report["test_rows"] = int(test_mask.sum())
        metrics[approach] = report
        for metric_name in ["precision", "recall", "f1", "roc_auc", "pr_auc", "false_positive_rate"]:
            model_metric_rows.append(
                {
                    "metric_id": f"MM{metric_row_number:04d}",
                    "run_id": "latest",
                    "approach": approach,
                    "metric_name": metric_name,
                    "metric_value": report[metric_name],
                    "split_name": "full_evaluation",
                }
            )
            metric_row_number += 1

    combined_score = approaches["rules + combined score"]
    precision_curve, recall_curve, curve_thresholds = precision_recall_curve(y, combined_score)
    threshold_analysis = []
    for threshold in [20, 30, 40, 50, 60, 70, 80, 90]:
        threshold_report = _classification_metrics(y, combined_score, threshold, amounts)
        threshold_analysis.append(
            {
                "threshold": threshold,
                "precision": threshold_report["precision"],
                "recall": threshold_report["recall"],
                "false_positive_rate": threshold_report["false_positive_rate"],
                "alert_volume": threshold_report["alert_volume"],
                "workload_minutes": threshold_report["investigation_workload_minutes"],
            }
        )

    coefficients = logistic.named_steps["model"].coef_[0]
    feature_importance = [
        {
            "feature": feature,
            "coefficient": round(float(coefficient), 6),
            "absolute_importance": round(abs(float(coefficient)), 6),
        }
        for feature, coefficient in sorted(
            zip(feature_names, coefficients), key=lambda item: abs(item[1]), reverse=True
        )
    ]
    artifacts = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "class_distribution": {
            "normal": int((y == 0).sum()),
            "fraud": int((y == 1).sum()),
            "fraud_rate": round(float(y.mean()), 6),
        },
        "time_split": {
            "train_rows": int(train_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "train_end": tx.loc[split_index - 1, "timestamp"].isoformat(),
            "test_start": tx.loc[split_index, "timestamp"].isoformat() if test_mask.any() else None,
        },
        "metrics": metrics,
        "threshold_analysis": threshold_analysis,
        "precision_recall_curve": {
            "precision": [round(float(value), 6) for value in precision_curve[:: max(1, len(precision_curve) // 60)]],
            "recall": [round(float(value), 6) for value in recall_curve[:: max(1, len(recall_curve) // 60)]],
            "thresholds": [round(float(value), 6) for value in curve_thresholds[:: max(1, len(curve_thresholds) // 60)]],
        },
        "feature_importance": feature_importance[:20],
        "model_limitations": [
            "The labels and behaviors are synthetic and may not reflect real fraud patterns.",
            "Accuracy is not a primary metric because fraud is a rare class.",
            "Risk scores prioritize investigation and do not prove fraud.",
            "Human review is required before customer-impacting action.",
            "A production model would require calibration, drift monitoring and fairness review.",
        ],
    }
    signals = pd.DataFrame(
        {
            "transaction_id": tx["transaction_id"],
            "logistic_probability": logistic_probability,
            "anomaly_score": anomaly_score,
        }
    )
    return signals, artifacts, model_metric_rows
