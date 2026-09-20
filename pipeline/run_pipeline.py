"""Command-line entry point for the reproducible Phase 1 pipeline.

Example:
    python -m pipeline.run_pipeline --seed 42
"""

import argparse
import json
from pathlib import Path

from pipeline.generator.config import load_generation_config
from pipeline.generator.database import persist_dataset
from pipeline.generator.generate import generate_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "pipeline" / "config" / "generation.yml"
DEFAULT_DB_URL = "sqlite:///./data/generated/fraud_command_center.db"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "generated" / "manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Fraud Command Center synthetic dataset"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--seed", type=int, default=None, help="Override the configured random seed"
    )
    parser.add_argument("--db", default=DEFAULT_DB_URL, help="SQLAlchemy database URL")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Append to an existing database instead of resetting it",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_generation_config(args.config)
    if args.seed is not None:
        config = config.with_overrides(seed=args.seed)
    bundle = generate_dataset(config)
    persist_dataset(bundle.tables, args.db, reset=not args.no_reset)

    manifest_path = args.manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(bundle.summary, indent=2), encoding="utf-8")

    print("Synthetic dataset generated successfully")
    print(json.dumps(bundle.summary, indent=2))
    print(f"Database: {args.db}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
