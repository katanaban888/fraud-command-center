"""Generators for relatively stable reference entities.

All values are intentionally synthetic and anonymized. Names are generated as
identifiers rather than copied from real people.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from pipeline.generator.config import GenerationConfig

CITY_LOCATIONS = [
    ("Central", "Tashkent", "UZ"),
    ("Samarkand", "Samarkand", "UZ"),
    ("Fergana", "Fergana", "UZ"),
    ("Almaty", "Almaty", "KZ"),
    ("Astana", "Astana", "KZ"),
    ("Istanbul", "Istanbul", "TR"),
    ("London", "London", "GB"),
    ("Berlin", "Berlin", "DE"),
    ("Dubai", "Dubai", "AE"),
    ("Singapore", "Singapore", "SG"),
    ("Mumbai", "Mumbai", "IN"),
    ("Paris", "Paris", "FR"),
]

COUNTRIES = [location[2] for location in CITY_LOCATIONS]
HIGH_RISK_COUNTRIES = {"IR", "KP", "SY"}
EXTRA_DEVICE_COUNTRIES = ["UZ", "KZ", "TR", "AE", "GB", "DE", "SG", "IN", "FR", "IR"]
OCCUPATIONS = [
    "Engineer",
    "Teacher",
    "Healthcare professional",
    "Consultant",
    "Retail worker",
    "Small business owner",
    "Student",
    "Finance professional",
    "Operations specialist",
    "Freelancer",
]


def _random_datetime(rng: np.random.Generator, start: datetime, end: datetime) -> datetime:
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=int(rng.integers(0, max(seconds, 1))))


def generate_customers(config: GenerationConfig, rng: np.random.Generator) -> pd.DataFrame:
    """Create anonymized customer profiles."""

    count = config.counts["customers"]
    customer_types = rng.choice(
        ["standard_customer", "high_value_customer", "small_business", "new_customer"],
        size=count,
        p=[0.62, 0.12, 0.14, 0.12],
    )
    risk_levels = rng.choice(["Low", "Medium", "High"], size=count, p=[0.76, 0.18, 0.06])
    locations = rng.choice(len(CITY_LOCATIONS), size=count)
    registration_offsets = rng.integers(0, 720, size=count)
    start_date = config.start_date.date()
    registration_dates = [
        start_date - timedelta(days=int(offset)) for offset in registration_offsets
    ]

    income_base = np.where(
        customer_types == "small_business",
        rng.lognormal(mean=np.log(7_000), sigma=0.45, size=count),
        np.where(
            customer_types == "high_value_customer",
            rng.lognormal(mean=np.log(5_500), sigma=0.40, size=count),
            rng.lognormal(mean=np.log(2_200), sigma=0.50, size=count),
        ),
    )
    # A small group of higher risk customers deliberately has noisier profiles.
    income = np.round(np.clip(income_base, 400, 250_000), 2)

    return pd.DataFrame(
        {
            "customer_id": [f"CUS{i:05d}" for i in range(1, count + 1)],
            "anonymized_name": [f"Customer {i:05d}" for i in range(1, count + 1)],
            "age": rng.integers(18, 76, size=count),
            "gender": rng.choice(
                ["Female", "Male", "Non-binary", "Undisclosed"],
                size=count,
                p=[0.47, 0.47, 0.02, 0.04],
            ),
            "region": [CITY_LOCATIONS[int(index)][0] for index in locations],
            "city": [CITY_LOCATIONS[int(index)][1] for index in locations],
            "customer_type": customer_types,
            "registration_date": registration_dates,
            "occupation": rng.choice(OCCUPATIONS, size=count),
            "monthly_income": income,
            "customer_risk_level": risk_levels,
            "is_verified": rng.random(size=count) < 0.93,
        }
    )


def generate_accounts(
    config: GenerationConfig,
    customers: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Create at least one account per customer and a second account for a subset."""

    count = config.counts["accounts"]
    customer_ids = customers["customer_id"].tolist()
    additional = count - len(customer_ids)
    if additional < 0:
        raise ValueError("The account count must be at least the customer count")

    owners = customer_ids + rng.choice(customer_ids, size=additional, replace=True).tolist()
    rng.shuffle(owners)
    customer_lookup = customers.set_index("customer_id").to_dict("index")
    rows: list[dict] = []

    for index, customer_id in enumerate(owners, start=1):
        profile = customer_lookup[customer_id]
        registration = profile["registration_date"]
        max_opening_offset = max((config.start_date.date() - registration).days, 1)
        opening_date = registration + timedelta(days=int(rng.integers(0, max_opening_offset + 1)))
        account_type = rng.choice(["current", "savings", "business"], p=[0.62, 0.28, 0.10])
        currency = rng.choice(["USD", "EUR", "GBP", "UZS"], p=[0.46, 0.18, 0.10, 0.26])
        income = float(profile["monthly_income"])
        balance = float(np.clip(rng.lognormal(np.log(max(income * 1.8, 500)), 0.80), 100, 500_000))
        rows.append(
            {
                "account_id": f"ACC{index:05d}",
                "customer_id": customer_id,
                "account_type": account_type,
                "currency": currency,
                "opening_date": opening_date,
                "initial_balance": round(balance, 2),
                "current_balance": round(balance, 2),
                "account_status": rng.choice(["Active", "Dormant"], p=[0.97, 0.03]),
            }
        )
    return pd.DataFrame(rows)


def generate_devices(
    config: GenerationConfig,
    customers: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create devices plus a many-to-many customer/device relationship table."""

    count = config.counts["devices"]
    customer_ids = customers["customer_id"].tolist()
    customer_locations = customers.set_index("customer_id")["city"].to_dict()
    customer_country = {
        row.customer_id: next(
            (country for _, city, country in CITY_LOCATIONS if city == row.city), "UZ"
        )
        for row in customers.itertuples()
    }
    primary_customers = rng.choice(customer_ids, size=count, replace=True)
    device_rows: list[dict] = []
    link_rows: list[dict] = []

    for index, primary_customer in enumerate(primary_customers, start=1):
        first_seen = _random_datetime(
            rng, config.start_date - timedelta(days=60), config.start_date
        )
        last_seen = _random_datetime(rng, config.start_date, config.end_date)
        device_id = f"DEV{index:05d}"
        country = customer_country[primary_customer]
        city = customer_locations[primary_customer]
        device_rows.append(
            {
                "device_id": device_id,
                "customer_id": primary_customer,
                "device_type": rng.choice(["Mobile", "Desktop", "Tablet"], p=[0.70, 0.23, 0.07]),
                "operating_system": rng.choice(
                    ["iOS", "Android", "Windows", "macOS", "Linux"],
                    p=[0.32, 0.43, 0.12, 0.10, 0.03],
                ),
                "ip_address": f"10.{int(rng.integers(0, 256))}.{int(rng.integers(0, 256))}.{int(rng.integers(1, 255))}",
                "country": country,
                "city": city,
                "first_seen_at": first_seen,
                "last_seen_at": last_seen,
                "device_risk_score": round(float(rng.uniform(2, 28)), 2),
            }
        )
        link_rows.append(
            {
                "device_id": device_id,
                "customer_id": primary_customer,
                "first_seen_at": first_seen,
                "last_seen_at": last_seen,
                "is_primary": True,
            }
        )

    device_ids = [f"DEV{i:05d}" for i in range(1, count + 1)]
    device_by_id = {row["device_id"]: row for row in device_rows}
    existing_links = {(row["device_id"], row["customer_id"]) for row in link_rows}
    # Ensure every customer has a device, while a subset deliberately shares devices.
    primary_by_customer: dict[str, str] = {}
    for customer_id in customer_ids:
        primary_device = str(rng.choice(device_ids))
        primary_by_customer[customer_id] = primary_device
        link_key = (primary_device, customer_id)
        if link_key not in existing_links:
            device_row = device_by_id[primary_device]
            link_rows.append(
                {
                    "device_id": primary_device,
                    "customer_id": customer_id,
                    "first_seen_at": device_row["first_seen_at"],
                    "last_seen_at": device_row["last_seen_at"],
                    "is_primary": True,
                }
            )
            existing_links.add(link_key)

    # Some customers use a second device; this is useful for later new-device features.
    for customer_id in customer_ids:
        if rng.random() < 0.18:
            second_device = str(rng.choice(device_ids))
            link_key = (second_device, customer_id)
            if second_device != primary_by_customer[customer_id] and link_key not in existing_links:
                device_row = device_by_id[second_device]
                link_rows.append(
                    {
                        "device_id": second_device,
                        "customer_id": customer_id,
                        "first_seen_at": device_row["first_seen_at"],
                        "last_seen_at": device_row["last_seen_at"],
                        "is_primary": False,
                    }
                )
                existing_links.add(link_key)

    links = pd.DataFrame(link_rows).drop_duplicates(subset=["device_id", "customer_id"])
    link_counts = links.groupby("device_id")["customer_id"].nunique().to_dict()
    devices = pd.DataFrame(device_rows)
    devices["device_risk_score"] = devices.apply(
        lambda row: round(
            min(
                100.0,
                float(row["device_risk_score"])
                + max(link_counts.get(row["device_id"], 1) - 1, 0) * 12,
            ),
            2,
        ),
        axis=1,
    )
    # The requested device.customer_id is kept as a primary/representative owner;
    # device_customer_links is the authoritative many-to-many relationship.
    return devices, links


def generate_beneficiaries(
    config: GenerationConfig,
    rng: np.random.Generator,
) -> pd.DataFrame:
    count = config.counts["beneficiaries"]
    beneficiary_countries = rng.choice(
        COUNTRIES + ["IR", "KP", "SY"],
        size=count,
        # The explicit weights are normalized to protect small custom configs
        # from floating-point rounding while keeping risky countries rare.
        p=(
            np.array(
                [
                    0.18,
                    0.08,
                    0.08,
                    0.08,
                    0.08,
                    0.08,
                    0.08,
                    0.07,
                    0.07,
                    0.06,
                    0.06,
                    0.04,
                    0.02,
                    0.02,
                    0.02,
                ]
            )
            / np.array(
                [
                    0.18,
                    0.08,
                    0.08,
                    0.08,
                    0.08,
                    0.08,
                    0.08,
                    0.07,
                    0.07,
                    0.06,
                    0.06,
                    0.04,
                    0.02,
                    0.02,
                    0.02,
                ]
            ).sum()
        ),
    )
    regions = rng.choice(
        ["Domestic", "Europe", "Central Asia", "Middle East", "Asia Pacific"], size=count
    )
    created_at = [
        _random_datetime(rng, config.start_date - timedelta(days=180), config.end_date)
        for _ in range(count)
    ]
    risk = rng.choice(["Low", "Medium", "High"], size=count, p=[0.76, 0.18, 0.06])
    risk[np.isin(beneficiary_countries, list(HIGH_RISK_COUNTRIES))] = "High"
    return pd.DataFrame(
        {
            "beneficiary_id": [f"BEN{i:05d}" for i in range(1, count + 1)],
            "beneficiary_type": rng.choice(
                ["Individual", "Merchant", "Corporate", "Charity"],
                size=count,
                p=[0.45, 0.35, 0.15, 0.05],
            ),
            "country": beneficiary_countries,
            "region": regions,
            "category": rng.choice(
                [
                    "Retail",
                    "Utilities",
                    "Payroll",
                    "Marketplace",
                    "Investment",
                    "Remittance",
                    "Other",
                ],
                size=count,
            ),
            "beneficiary_risk_level": risk,
            "created_at": created_at,
        }
    )
