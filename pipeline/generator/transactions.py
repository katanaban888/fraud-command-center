"""Synthetic transaction timeline and fraud-scenario generator."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from pipeline.generator.config import GenerationConfig
from pipeline.generator.entities import CITY_LOCATIONS

CREDIT_TYPES = {"salary_credit", "cash_deposit", "refund"}
NORMAL_TRANSACTION_TYPE_POOL = np.array(
    [
        "card_purchase",
        "card_purchase",
        "card_purchase",
        "card_purchase",
        "utility_payment",
        "utility_payment",
        "subscription_payment",
        "peer_transfer",
        "peer_transfer",
        "peer_transfer",
        "business_payment",
        "salary_credit",
        "cash_deposit",
        "refund",
        "cash_withdrawal",
    ]
)
COMPLETION_STATUS_POOL = np.array(["completed"] * 985 + ["pending"] * 10 + ["declined"] * 5)
NORMAL_AMOUNT_PARAMETERS = {
    "card_purchase": (np.log(45), 0.70),
    "utility_payment": (np.log(90), 0.45),
    "subscription_payment": (np.log(28), 0.35),
    "peer_transfer": (np.log(240), 0.90),
    "business_payment": (np.log(850), 0.80),
    "salary_credit": (np.log(2_700), 0.35),
    "cash_deposit": (np.log(700), 0.80),
    "refund": (np.log(120), 0.50),
    "cash_withdrawal": (np.log(180), 0.65),
}
FRAUD_SCENARIOS = [
    "night_new_device",
    "unusual_amount_spike",
    "rapid_beneficiary_transfers",
    "new_beneficiary_balance_depletion",
    "shared_device_activity",
    "many_new_beneficiaries",
    "cross_border_activity",
    "circular_account_flow",
    "structuring_pattern",
    "high_risk_customer_behavior",
    "account_takeover_pattern",
    "synthetic_network_cluster",
]


def _random_timestamp(rng: np.random.Generator, config: GenerationConfig) -> datetime:
    total_seconds = config.days * 24 * 60 * 60
    return config.start_date + timedelta(seconds=int(rng.integers(0, total_seconds)))


def _night_timestamp(rng: np.random.Generator, config: GenerationConfig) -> datetime:
    day = int(rng.integers(0, config.days))
    hour = int(rng.integers(1, 5))
    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))
    return config.start_date + timedelta(days=day, hours=hour, minutes=minute, seconds=second)


def _city_country(city: str) -> str:
    return next((country for _, known_city, country in CITY_LOCATIONS if known_city == city), "UZ")


def _make_customer_maps(
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    device_links: pd.DataFrame,
) -> tuple[dict, dict, dict]:
    customer_accounts = accounts.groupby("customer_id")["account_id"].apply(list).to_dict()
    customer_devices = device_links.groupby("customer_id")["device_id"].apply(list).to_dict()
    account_to_customer = accounts.set_index("account_id")["customer_id"].to_dict()
    # Defensive defaults keep the generator useful with small custom test configs.
    for customer_id in customers["customer_id"]:
        customer_accounts.setdefault(customer_id, [])
        customer_devices.setdefault(customer_id, [])
    return customer_accounts, customer_devices, account_to_customer


def _build_preferred_beneficiaries(
    customers: pd.DataFrame,
    beneficiaries: pd.DataFrame,
    rng: np.random.Generator,
) -> dict[str, list[str]]:
    beneficiary_ids = beneficiaries["beneficiary_id"].tolist()
    preferred: dict[str, list[str]] = {}
    for customer_id in customers["customer_id"]:
        size = int(rng.integers(1, 5))
        # Sampling integer positions with replacement is much faster for the
        # large default dataset; de-duplication still creates a short personal
        # history and does not affect the fraud labels.
        positions = rng.integers(0, len(beneficiary_ids), size=size * 2)
        preferred[customer_id] = list(
            dict.fromkeys(beneficiary_ids[int(position)] for position in positions)
        )[:size]
    return preferred


def _generate_normal_transactions(
    *,
    count: int,
    rng: np.random.Generator,
    config: GenerationConfig,
    customer_devices: dict[str, list[str]],
    preferred_beneficiaries: dict[str, list[str]],
    beneficiary_ids: list[str],
    device_lookup: dict[str, dict],
    account_lookup: dict[str, dict],
    customer_lookup: dict[str, dict],
    account_ids: list[str],
) -> pd.DataFrame:
    """Generate normal events in vectorized batches for a fast 50k-row seed."""

    account_index = rng.integers(0, len(account_ids), size=count)
    selected_accounts = np.asarray(account_ids, dtype=object)[account_index]
    selected_customers = np.asarray(
        [account_lookup[str(account_id)]["customer_id"] for account_id in selected_accounts],
        dtype=object,
    )
    transaction_types = rng.choice(NORMAL_TRANSACTION_TYPE_POOL, size=count)
    amounts = np.zeros(count, dtype=float)
    for transaction_type, (mean, sigma) in NORMAL_AMOUNT_PARAMETERS.items():
        mask = transaction_types == transaction_type
        amounts[mask] = rng.lognormal(mean, sigma, size=int(mask.sum()))
    amounts = np.clip(amounts, 2, 100_000).round(2)

    timestamps = [
        config.start_date + timedelta(seconds=int(seconds))
        for seconds in rng.integers(0, config.days * 24 * 60 * 60, size=count)
    ]
    selected_devices = np.asarray(
        [customer_devices[str(customer_id)][0] for customer_id in selected_customers],
        dtype=object,
    )
    device_rows = [device_lookup[str(device_id)] for device_id in selected_devices]
    countries = np.asarray([row["country"] for row in device_rows], dtype=object)
    cities = np.asarray([row["city"] for row in device_rows], dtype=object)
    travel_mask = rng.random(count) < 0.08
    travel_indices = rng.integers(0, len(CITY_LOCATIONS), size=int(travel_mask.sum()))
    if travel_mask.any():
        cities[travel_mask] = [CITY_LOCATIONS[int(index)][1] for index in travel_indices]
        countries[travel_mask] = [CITY_LOCATIONS[int(index)][2] for index in travel_indices]

    beneficiary_values = np.asarray(
        [preferred_beneficiaries[str(customer_id)][0] for customer_id in selected_customers],
        dtype=object,
    )
    random_beneficiary_mask = rng.random(count) >= 0.78
    beneficiary_values[random_beneficiary_mask] = rng.choice(
        beneficiary_ids, size=int(random_beneficiary_mask.sum())
    )

    channels = np.empty(count, dtype=object)
    card_mask = np.isin(
        transaction_types, ["card_purchase", "subscription_payment", "utility_payment"]
    )
    channels[card_mask] = rng.choice(["Card", "Mobile App", "Web"], size=int(card_mask.sum()))
    atm_mask = transaction_types == "cash_withdrawal"
    channels[atm_mask] = "ATM"
    business_mask = (
        np.asarray(
            [
                customer_lookup[str(customer_id)]["customer_type"] == "small_business"
                for customer_id in selected_customers
            ]
        )
        & ~card_mask
        & ~atm_mask
    )
    channels[business_mask] = rng.choice(
        ["Web", "API", "Mobile App"], size=int(business_mask.sum())
    )
    other_mask = ~(card_mask | atm_mask | business_mask)
    channels[other_mask] = rng.choice(["Mobile App", "Web", "API"], size=int(other_mask.sum()))

    result = pd.DataFrame(
        {
            "timestamp": timestamps,
            "sender_account_id": selected_accounts,
            "sender_customer_id": selected_customers,
            "beneficiary_id": beneficiary_values,
            "device_id": selected_devices,
            "channel": channels,
            "transaction_type": transaction_types,
            "amount": amounts,
            "currency": [
                account_lookup[str(account_id)]["currency"] for account_id in selected_accounts
            ],
            "country": countries,
            "city": cities,
            "status": rng.choice(COMPLETION_STATUS_POOL, size=count),
            "is_fraud": False,
            "fraud_scenario": "normal",
            "data_source": "synthetic_generator",
        }
    )
    return result


def _normal_transaction(
    *,
    rng: np.random.Generator,
    config: GenerationConfig,
    account_id: str,
    customer_id: str,
    customer_devices: dict[str, list[str]],
    preferred_beneficiaries: dict[str, list[str]],
    beneficiary_ids: list[str],
    device_lookup: dict[str, dict],
    account_lookup: dict[str, dict],
    customer_lookup: dict[str, dict],
) -> dict:
    transaction_type = str(rng.choice(NORMAL_TRANSACTION_TYPE_POOL))
    mean, sigma = NORMAL_AMOUNT_PARAMETERS[transaction_type]
    amount = min(max(float(rng.lognormal(mean, sigma)), 2.0), 100_000.0)
    device_id = str(rng.choice(customer_devices[customer_id]))
    device = device_lookup[device_id]
    if rng.random() < 0.78:
        beneficiary_id = str(rng.choice(preferred_beneficiaries[customer_id]))
    else:
        beneficiary_id = str(rng.choice(beneficiary_ids))

    city = device["city"]
    country = device["country"]
    # Travel is normal behavior in the synthetic population, but changes geography.
    if rng.random() < 0.08:
        _, city, country = CITY_LOCATIONS[int(rng.integers(0, len(CITY_LOCATIONS)))]

    if transaction_type in {"card_purchase", "subscription_payment", "utility_payment"}:
        channel = str(rng.choice(["Card", "Mobile App", "Web"]))
    elif transaction_type == "cash_withdrawal":
        channel = "ATM"
    elif customer_lookup[customer_id]["customer_type"] == "small_business":
        channel = str(rng.choice(["Web", "API", "Mobile App"]))
    else:
        channel = str(rng.choice(["Mobile App", "Web", "API"]))

    status = str(rng.choice(COMPLETION_STATUS_POOL))
    return {
        "timestamp": _random_timestamp(rng, config),
        "sender_account_id": account_id,
        "sender_customer_id": customer_id,
        "beneficiary_id": beneficiary_id,
        "device_id": device_id,
        "channel": channel,
        "transaction_type": transaction_type,
        "amount": round(amount, 2),
        "currency": account_lookup[account_id]["currency"],
        "country": country,
        "city": city,
        "status": status,
        "is_fraud": False,
        "fraud_scenario": "normal",
        "data_source": "synthetic_generator",
    }


def _fraud_transaction(
    *,
    index: int,
    rng: np.random.Generator,
    config: GenerationConfig,
    customer_id: str,
    account_id: str,
    customer_devices: dict[str, list[str]],
    preferred_beneficiaries: dict[str, list[str]],
    beneficiary_ids: list[str],
    high_risk_beneficiaries: list[str],
    shared_devices: list[str],
    device_lookup: dict[str, dict],
    account_lookup: dict[str, dict],
    customer_lookup: dict[str, dict],
) -> dict:
    scenario = FRAUD_SCENARIOS[index % len(FRAUD_SCENARIOS)]
    timestamp = (
        _night_timestamp(rng, config)
        if scenario == "night_new_device"
        else _random_timestamp(rng, config)
    )
    device_id = str(rng.choice(customer_devices[customer_id]))
    if scenario in {"night_new_device", "account_takeover_pattern"}:
        unfamiliar_devices = [
            device for device in device_lookup if device not in customer_devices[customer_id]
        ]
        if unfamiliar_devices:
            device_id = str(rng.choice(unfamiliar_devices))
    elif scenario in {"shared_device_activity", "synthetic_network_cluster"} and shared_devices:
        device_id = str(rng.choice(shared_devices))

    beneficiary_id = str(rng.choice(beneficiary_ids))
    if scenario in {
        "new_beneficiary_balance_depletion",
        "many_new_beneficiaries",
        "account_takeover_pattern",
    }:
        unfamiliar_beneficiaries = [
            beneficiary
            for beneficiary in beneficiary_ids
            if beneficiary not in preferred_beneficiaries[customer_id]
        ]
        if unfamiliar_beneficiaries:
            beneficiary_id = str(rng.choice(unfamiliar_beneficiaries))
    elif (
        scenario in {"rapid_beneficiary_transfers", "synthetic_network_cluster"}
        and high_risk_beneficiaries
    ):
        beneficiary_id = str(rng.choice(high_risk_beneficiaries))
    elif scenario == "circular_account_flow":
        beneficiary_id = "BEN00001" if "BEN00001" in beneficiary_ids else beneficiary_id

    account = account_lookup[account_id]
    customer = customer_lookup[customer_id]
    base_amount = float(account["initial_balance"])
    amount = float(np.clip(rng.lognormal(np.log(max(base_amount * 0.08, 100)), 0.75), 10, 250_000))
    if scenario == "unusual_amount_spike":
        amount = float(np.clip(base_amount * rng.uniform(0.25, 0.80), 100, 250_000))
    elif scenario == "rapid_beneficiary_transfers":
        amount = float(rng.uniform(120, 1_500))
    elif scenario == "new_beneficiary_balance_depletion":
        amount = max(100, base_amount * rng.uniform(0.75, 0.95))
    elif scenario == "structuring_pattern":
        amount = float(rng.uniform(850, 995))
    elif scenario == "high_risk_customer_behavior":
        amount = float(np.clip(customer["monthly_income"] * rng.uniform(2, 5), 500, 200_000))
    elif scenario == "cross_border_activity":
        amount = float(rng.uniform(500, 8_000))
    elif scenario == "many_new_beneficiaries":
        amount = float(rng.uniform(80, 800))

    device = device_lookup[device_id]
    country = device["country"]
    city = device["city"]
    if scenario == "cross_border_activity":
        alternatives = [location for location in CITY_LOCATIONS if location[2] != country]
        _, city, country = alternatives[int(rng.integers(0, len(alternatives)))]
    elif scenario in {"night_new_device", "account_takeover_pattern"}:
        # The device itself supplies a location that can differ from the customer's usual city.
        country = device["country"]
        city = device["city"]

    return {
        "timestamp": timestamp,
        "sender_account_id": account_id,
        "sender_customer_id": customer_id,
        "beneficiary_id": beneficiary_id,
        "device_id": device_id,
        "channel": str(rng.choice(["Mobile App", "Web", "API"])),
        "transaction_type": "transfer",
        "amount": round(amount, 2),
        "currency": account["currency"],
        "country": country,
        "city": city,
        "status": "completed",
        "is_fraud": True,
        "fraud_scenario": scenario,
        "data_source": "synthetic_generator",
    }


def _apply_balances(
    records: list[dict], accounts: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    balances = accounts.set_index("account_id")["initial_balance"].astype(float).to_dict()
    output: list[dict] = []
    for record in sorted(records, key=lambda row: row["timestamp"]):
        account_id = record["sender_account_id"]
        before = max(float(balances[account_id]), 0.0)
        amount = max(float(record["amount"]), 0.01)
        if record["status"] != "completed":
            after = before
        elif record["transaction_type"] in CREDIT_TYPES:
            after = before + amount
        else:
            if record["fraud_scenario"] == "new_beneficiary_balance_depletion":
                amount = max(0.01, before * rng.uniform(0.90, 0.98))
            amount = min(amount, max(before, 0.01))
            after = max(before - amount, 0.0)
        balances[account_id] = after
        record = {
            **record,
            "amount": round(amount, 2),
            "balance_before": round(before, 2),
            "balance_after": round(after, 2),
        }
        output.append(record)

    result = pd.DataFrame(output)
    result.insert(0, "transaction_id", [f"TXN{i:06d}" for i in range(1, len(result) + 1)])
    final_balances = result.groupby("sender_account_id")["balance_after"].last().to_dict()
    accounts["current_balance"] = accounts.apply(
        lambda row: round(float(final_balances.get(row["account_id"], row["initial_balance"])), 2),
        axis=1,
    )
    return result


def generate_transactions(
    config: GenerationConfig,
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    devices: pd.DataFrame,
    device_links: pd.DataFrame,
    beneficiaries: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Generate a sorted transaction timeline with labeled synthetic scenarios."""

    count = config.counts["transactions"]
    customer_accounts, customer_devices, _ = _make_customer_maps(customers, accounts, device_links)
    if any(not account_list for account_list in customer_accounts.values()):
        raise ValueError("Every customer must have at least one account")
    if any(not device_list for device_list in customer_devices.values()):
        raise ValueError("Every customer must have at least one device")

    account_lookup = accounts.set_index("account_id").to_dict("index")
    customer_lookup = customers.set_index("customer_id").to_dict("index")
    device_lookup = devices.set_index("device_id").to_dict("index")
    beneficiary_ids = beneficiaries["beneficiary_id"].tolist()
    high_risk_beneficiaries = beneficiaries.loc[
        beneficiaries["beneficiary_risk_level"] == "High", "beneficiary_id"
    ].tolist()
    preferred_beneficiaries = _build_preferred_beneficiaries(customers, beneficiaries, rng)
    shared_device_counts = device_links.groupby("device_id")["customer_id"].nunique()
    shared_devices = shared_device_counts[shared_device_counts >= 3].index.tolist()
    if not shared_devices:
        shared_devices = shared_device_counts.nlargest(
            min(10, len(shared_device_counts))
        ).index.tolist()

    fraud_count = min(count - 1, max(len(FRAUD_SCENARIOS), round(count * config.fraud_rate_target)))
    normal_count = count - fraud_count
    customer_ids = customers["customer_id"].tolist()
    account_ids = accounts["account_id"].tolist()
    normal_frame = _generate_normal_transactions(
        count=normal_count,
        rng=rng,
        config=config,
        customer_devices=customer_devices,
        preferred_beneficiaries=preferred_beneficiaries,
        beneficiary_ids=beneficiary_ids,
        device_lookup=device_lookup,
        account_lookup=account_lookup,
        customer_lookup=customer_lookup,
        account_ids=account_ids,
    )
    records: list[dict] = normal_frame.to_dict("records")

    high_risk_customers = customers.loc[
        customers["customer_risk_level"] == "High", "customer_id"
    ].tolist()
    for index in range(fraud_count):
        scenario = FRAUD_SCENARIOS[index % len(FRAUD_SCENARIOS)]
        if scenario == "high_risk_customer_behavior" and high_risk_customers:
            customer_id = str(rng.choice(high_risk_customers))
        else:
            customer_id = str(rng.choice(customer_ids))
        account_id = str(rng.choice(customer_accounts[customer_id]))
        records.append(
            _fraud_transaction(
                index=index,
                rng=rng,
                config=config,
                customer_id=customer_id,
                account_id=account_id,
                customer_devices=customer_devices,
                preferred_beneficiaries=preferred_beneficiaries,
                beneficiary_ids=beneficiary_ids,
                high_risk_beneficiaries=high_risk_beneficiaries,
                shared_devices=shared_devices,
                device_lookup=device_lookup,
                account_lookup=account_lookup,
                customer_lookup=customer_lookup,
            )
        )

    result = _apply_balances(records, accounts, rng)
    return result[
        [
            "transaction_id",
            "timestamp",
            "sender_account_id",
            "sender_customer_id",
            "beneficiary_id",
            "device_id",
            "channel",
            "transaction_type",
            "amount",
            "currency",
            "country",
            "city",
            "status",
            "balance_before",
            "balance_after",
            "is_fraud",
            "fraud_scenario",
            "data_source",
        ]
    ]
