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
from pipeline.scoring.risk_score import build_alert_tables, score_transactions
from tests.test_data_generation import small_config


def test_risk_scores_are_bounded_and_explainable():
    config = small_config()
    rng = np.random.default_rng(config.seed)
    customers = generate_customers(config, rng)
    accounts = generate_accounts(config, customers, rng)
    devices, links = generate_devices(config, customers, rng)
    beneficiaries = generate_beneficiaries(config, rng)
    transactions = generate_transactions(config, customers, accounts, devices, links, beneficiaries, rng)
    features = engineer_features(transactions, customers, accounts, devices, links, beneficiaries)
    rules = evaluate_rules(transactions, features, customers, version="V2")
    scored, components = score_transactions(transactions, features, customers, devices, rules)
    alerts, alert_components = build_alert_tables(scored, components)

    assert scored["risk_score"].between(0, 100).all()
    assert set(scored["risk_level"]) <= {"Low", "Medium", "High", "Critical"}
    assert set(components["component_name"]) == {"rule_score", "behavioral_score", "customer_score", "device_score", "network_score", "geo_channel_score"}
    assert len(alert_components) == len(alerts) * 6
