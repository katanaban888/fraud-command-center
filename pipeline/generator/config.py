"""Configuration helpers for the reproducible synthetic data generator."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class GenerationConfig:
    seed: int
    start_date: datetime
    days: int
    counts: dict[str, int]
    fraud_rate_target: float

    @property
    def end_date(self) -> datetime:
        return self.start_date + timedelta(days=self.days)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> "GenerationConfig":
        raw_start = mapping.get("start_date", "2025-01-01T00:00:00+00:00")
        start_date = datetime.fromisoformat(str(raw_start).replace("Z", "+00:00"))
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        return cls(
            seed=int(mapping.get("seed", 42)),
            start_date=start_date,
            days=int(mapping.get("days", 120)),
            counts={key: int(value) for key, value in mapping["counts"].items()},
            fraud_rate_target=float(mapping.get("fraud_rate_target", 0.02)),
        )

    def with_overrides(
        self, *, seed: int | None = None, counts: dict[str, int] | None = None
    ) -> "GenerationConfig":
        return GenerationConfig(
            seed=self.seed if seed is None else seed,
            start_date=self.start_date,
            days=self.days,
            counts=self.counts if counts is None else {**self.counts, **counts},
            fraud_rate_target=self.fraud_rate_target,
        )


def load_generation_config(path: str | Path) -> GenerationConfig:
    with Path(path).open("r", encoding="utf-8") as file:
        mapping = yaml.safe_load(file) or {}
    return GenerationConfig.from_mapping(mapping)
