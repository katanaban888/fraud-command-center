"""Command-line entry point for the complete reproducible pipeline.

Example:
    python -m pipeline.run_pipeline --seed 42

The raw generator remains available as ``generate_dataset`` for unit tests.
The default command runs raw generation, features, rules, score, ML evaluation,
data quality and insight creation before writing a local database.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from pipeline.analytics.performance import build_rule_performance
from pipeline.features.engineering import engineer_features
from pipeline.generator.config import load_generation_config
from pipeline.generator.database import persist_dataset
from pipeline.generator.generate import generate_dataset
from pipeline.insights.generate_insights import generate_insights
from pipeline.ml.evaluate import evaluate_models
from pipeline.quality.checks import run_quality_checks
from pipeline.rules.engine import evaluate_rules
from pipeline.scoring.risk_score import build_alert_tables, score_transactions

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "pipeline" / "config" / "generation.yml"
DEFAULT_DB_URL = "sqlite:///./data/generated/fraud_command_center.db"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "generated" / "manifest.json"
ANALYST_CONFIG = PROJECT_ROOT / "pipeline" / "config" / "analysts.yml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and analyze the Fraud Command Center dataset")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--seed", type=int, default=None, help="Override the configured random seed")
    parser.add_argument("--db", default=DEFAULT_DB_URL, help="SQLAlchemy database URL")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-only", action="store_true", help="Stop after raw entity and transaction generation")
    parser.add_argument("--no-reset", action="store_true", help="Append to an existing database instead of resetting it")
    return parser.parse_args()


def _read_analysts() -> pd.DataFrame:
    with ANALYST_CONFIG.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    return pd.DataFrame(payload.get("analysts", []))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str, allow_nan=False), encoding="utf-8")


def run_full_pipeline(config, database_url: str, manifest_path: Path, *, reset: bool = True) -> dict[str, Any]:
    bundle = generate_dataset(config)
    raw_tables = bundle.tables
    if not raw_tables["transactions"].empty:
        features = engineer_features(
            raw_tables["transactions"],
            raw_tables["customers"],
            raw_tables["accounts"],
            raw_tables["devices"],
            raw_tables["device_customer_links"],
            raw_tables["beneficiaries"],
        )
    else:
        features = pd.DataFrame()

    rule_v1 = evaluate_rules(
        raw_tables["transactions"], features, raw_tables["customers"], version="V1"
    )
    rule_v2 = evaluate_rules(
        raw_tables["transactions"], features, raw_tables["customers"], version="V2"
    )
    rule_score_frame = rule_v2.triggered_matrix[["transaction_id", "rule_score"]]
    ml_signals, model_artifacts, model_metric_rows = evaluate_models(
        raw_tables["transactions"], features, rule_score_frame
    )
    scored, score_components = score_transactions(
        raw_tables["transactions"],
        features,
        raw_tables["customers"],
        raw_tables["devices"],
        rule_v2,
        ml_signals=ml_signals,
    )
    alerts, alert_components = build_alert_tables(scored, score_components)
    rule_performance = build_rule_performance(
        {"V1": rule_v1, "V2": rule_v2}, raw_tables["transactions"]
    )
    quality_results, quality_artifacts = run_quality_checks(raw_tables)
    analytics_tables = {**raw_tables, "transaction_features": features}
    insights = generate_insights(analytics_tables, rule_performance)
    quality_artifacts["checks"] = quality_results.to_dict("records")
    analysts = _read_analysts()
    # Seed a small open queue from the highest-priority alerts. These are
    # pending cases with no synthetic decision, so the workflow remains honest.
    case_rows = []
    if not alerts.empty:
        analyst_ids = analysts["analyst_id"].tolist() if not analysts.empty else [None]
        for case_number, (_, alert) in enumerate(alerts.head(24).iterrows(), start=1):
            case_rows.append(
                {
                    "case_id": f"CASE{case_number:06d}",
                    "alert_id": alert["alert_id"],
                    "customer_id": alert["customer_id"],
                    "case_status": "Open",
                    "priority": alert["alert_priority"],
                    "assigned_analyst": analyst_ids[(case_number - 1) % len(analyst_ids)],
                    "opened_at": alert["created_at"],
                    "closed_at": None,
                    "final_decision": None,
                    "estimated_loss": None,
                    "prevented_loss": None,
                    "analyst_comment": "Synthetic queue seed; analyst review pending.",
                }
            )
    empty_cases = pd.DataFrame(case_rows, columns=[
        "case_id", "alert_id", "customer_id", "case_status", "priority",
        "assigned_analyst", "opened_at", "closed_at", "final_decision",
        "estimated_loss", "prevented_loss", "analyst_comment",
    ])
    rule_definitions = pd.DataFrame(rule_v2.definitions)
    rule_definitions["version"] = "V2"
    rule_definitions = rule_definitions[
        [
            "rule_id", "rule_name", "description", "category", "score", "severity", "enabled",
            "version", "threshold_v1", "threshold_v2",
        ]
    ]
    model_metrics = pd.DataFrame(model_metric_rows)
    tables = {
        **raw_tables,
        "transaction_features": features,
        "rule_definitions": rule_definitions,
        "rule_results": rule_v2.results,
        "alerts": alerts,
        "alert_score_components": alert_components,
        "analysts": analysts,
        "cases": empty_cases,
        "model_metrics": model_metrics,
        "data_quality_results": quality_results,
        "business_insights": insights,
    }
    persist_dataset(tables, database_url, reset=reset)

    manifest = {
        **bundle.summary,
        "pipeline_status": "complete",
        "analytics": {
            "feature_rows": int(len(features)),
            "triggered_rule_results": int(len(rule_v2.results)),
            "alerts": int(len(alerts)),
            "score_distribution": scored["risk_level"].value_counts().to_dict(),
            "quality_score": quality_artifacts["quality_score"],
            "quality_checks_failed": quality_artifacts["checks_failed"],
            "model_approaches": list(model_artifacts["metrics"]),
            "insights": int(len(insights)),
        },
    }
    output_dir = manifest_path.parent
    _write_json(output_dir / "model_metrics.json", model_artifacts)
    _write_json(output_dir / "rule_performance.json", rule_performance)
    _write_json(output_dir / "data_quality.json", quality_artifacts)
    _write_json(output_dir / "insights.json", {"insights": insights.to_dict("records")})
    _write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    args = parse_args()
    config = load_generation_config(args.config)
    if args.seed is not None:
        config = config.with_overrides(seed=args.seed)
    if args.raw_only:
        bundle = generate_dataset(config)
        persist_dataset(bundle.tables, args.db, reset=not args.no_reset)
        _write_json(args.manifest, bundle.summary)
        print(json.dumps(bundle.summary, indent=2, default=str))
        return
    manifest = run_full_pipeline(config, args.db, args.manifest, reset=not args.no_reset)
    print("Fraud Command Center pipeline completed")
    print(json.dumps(manifest, indent=2, default=str))
    print(f"Database: {args.db}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()
