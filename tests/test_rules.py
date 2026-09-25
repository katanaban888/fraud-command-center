import numpy as np

from pipeline.features.engineering import engineer_features
from pipeline.generator.entities import (
    generate_accounts,
    generate_beneficiaries,
    generate_customers,
    generate_devices,
)
from pipeline.generator.transactions import generate_transactions
from pipeline.rules.engine import evaluate_rules
from tests.test_data_generation import small_config


def make_rule_inputs():
    config = small_config()
    rng = np.random.default_rng(config.seed)
    customers = generate_customers(config, rng)
    accounts = generate_accounts(config, customers, rng)
    devices, links = generate_devices(config, customers, rng)
    beneficiaries = generate_beneficiaries(config, rng)
    transactions = generate_transactions(config, customers, accounts, devices, links, beneficiaries, rng)
    features = engineer_features(transactions, customers, accounts, devices, links, beneficiaries)
    return transactions, customers, features


def test_rules_return_explainable_results_for_both_versions():
    transactions, customers, features = make_rule_inputs()
    v1 = evaluate_rules(transactions, features, customers, version="V1")
    v2 = evaluate_rules(transactions, features, customers, version="V2")

    assert set(v1.triggered_matrix["transaction_id"]) == set(transactions["transaction_id"])
    assert set(v2.triggered_matrix["transaction_id"]) == set(transactions["transaction_id"])
    assert set(v2.results["rule_id"]).issubset({f"R{i:03d}" for i in range(1, 13)})
    assert v2.results["rule_reason"].str.len().gt(0).all()
    assert (v2.triggered_matrix["rule_score"] >= 0).all()
