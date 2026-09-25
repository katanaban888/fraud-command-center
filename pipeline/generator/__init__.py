"""Synthetic data generation package."""

from pipeline.generator.config import GenerationConfig
from pipeline.generator.generate import DatasetBundle, generate_dataset

__all__ = ["DatasetBundle", "GenerationConfig", "generate_dataset"]
