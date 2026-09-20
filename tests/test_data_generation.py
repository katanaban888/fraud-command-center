from pathlib import Path

import pandas as pd

from pipeline.generator.config import GenerationConfig, load_generation_config
from pipeline.generator.generate import generate_dataset


def small_config(seed: int = 42) -> GenerationConfig:
    base = load_generation_config(Path("pipeline/config/generation.yml"))
    return base.with_overrides(
        seed=seed,
        counts={
            "customers": 24,
            "accounts": 30,
            "devices": 12,
            "beneficiaries": 50,
            "transactions": 240,
        },
    )


def test_generator_has_expected_entity_counts():
    bundle = generate_dataset(small_config())

    assert len(bundle.tables["customers"]) == 24
    assert len(bundle.tables["accounts"]) == 30
    assert len(bundle.tables["devices"]) == 12
    assert len(bundle.tables["beneficiaries"]) == 50
    assert len(bundle.tables["transactions"]) == 240
    assert bundle.tables["transactions"]["transaction_id"].is_unique


def test_every_customer_has_an_account_and_device_link():
    bundle = generate_dataset(small_config())
    customers = set(bundle.tables["customers"]["customer_id"])
    account_owners = set(bundle.tables["accounts"]["customer_id"])
    device_owners = set(bundle.tables["device_customer_links"]["customer_id"])

    assert customers <= account_owners
    assert customers <= device_owners


def test_generator_is_reproducible_for_same_seed():
    first = generate_dataset(small_config(seed=123))
    second = generate_dataset(small_config(seed=123))

    for table_name in first.tables:
        pd.testing.assert_frame_equal(
            first.tables[table_name].reset_index(drop=True),
            second.tables[table_name].reset_index(drop=True),
            check_dtype=False,
        )


def test_fraud_labels_are_rare_and_scenarios_are_present():
    bundle = generate_dataset(small_config())
    transactions = bundle.tables["transactions"]

    fraud_rate = transactions["is_fraud"].mean()
    assert 0 < fraud_rate < 0.20
    scenarios = set(transactions.loc[transactions["is_fraud"], "fraud_scenario"])
    assert {"night_new_device", "structuring_pattern", "high_risk_customer_behavior"} <= scenarios


def test_balances_and_amounts_are_valid():
    transactions = generate_dataset(small_config()).tables["transactions"]

    assert (transactions["amount"] > 0).all()
    assert (transactions["balance_before"] >= 0).all()
    assert (transactions["balance_after"] >= 0).all()
    assert (
        transactions["balance_after"]
        <= transactions["balance_before"] + transactions["amount"] + 0.01
    ).all()
