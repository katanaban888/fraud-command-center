
from pipeline.features.engineering import engineer_features
from pipeline.generator.entities import (
    generate_accounts,
    generate_beneficiaries,
    generate_customers,
    generate_devices,
)
from pipeline.generator.transactions import generate_transactions
from tests.test_data_generation import small_config


def make_tables():
    config = small_config()
    import numpy as np

    rng = np.random.default_rng(config.seed)
    customers = generate_customers(config, rng)
    accounts = generate_accounts(config, customers, rng)
    devices, links = generate_devices(config, customers, rng)
    beneficiaries = generate_beneficiaries(config, rng)
    transactions = generate_transactions(config, customers, accounts, devices, links, beneficiaries, rng)
    return transactions, customers, accounts, devices, links, beneficiaries


def test_features_are_chronological_and_label_free():
    transactions, customers, accounts, devices, links, beneficiaries = make_tables()
    features = engineer_features(transactions, customers, accounts, devices, links, beneficiaries)

    assert len(features) == len(transactions)
    assert "is_fraud" not in features.columns
    assert features["transaction_id"].is_unique
    assert features["balance_depletion_ratio"].between(0, 1).all()
    assert features["amount_vs_customer_average"].notna().all()
    first_ids = transactions.sort_values("timestamp").groupby("sender_customer_id").first()["transaction_id"]
    first_features = features[features["transaction_id"].isin(set(first_ids))]
    assert (first_features["amount_vs_customer_average"] == 1).all()
