# Data dictionary

Fraud Command Center uses a synthetic dataset generated locally with a fixed random seed. The values are designed for portfolio demonstration and do not represent real customers, accounts, devices, IP addresses or financial activity.

## Entity tables

| Table | Grain | Primary key | Purpose |
|---|---|---|---|
| `customers` | One row per customer | `customer_id` | Anonymized customer profile and risk segment. |
| `accounts` | One row per account | `account_id` | Customer-owned account and simulated balance. |
| `devices` | One row per canonical device | `device_id` | Device metadata and baseline device risk. |
| `device_customer_links` | One row per customer-device relationship | `device_id`, `customer_id` | Supports shared-device analysis. |
| `beneficiaries` | One row per destination | `beneficiary_id` | Destination profile and beneficiary risk. |
| `transactions` | One row per financial transaction | `transaction_id` | Chronological transaction fact table and synthetic ground truth. |
| `transaction_features` | One row per transaction | `transaction_id` | Leakage-safe behavioral and network features; populated in Phase 2. |
| `rule_results` | One row per transaction-rule evaluation | `rule_result_id` | Explainable rule outcomes; populated in Phase 2. |
| `alerts` | One row per prioritized alert | `alert_id` | Investigation queue; populated in Phase 2. |
| `alert_score_components` | One row per alert-score component | `alert_id`, `component_name` | Contribution breakdown for risk explainability. |
| `cases` | One row per investigation case | `case_id` | Analyst workflow and outcomes. |

## `customers`

- `customer_id`: synthetic stable identifier, for example `CUS00001`.
- `anonymized_name`: display-safe label such as `Customer 00001`.
- `customer_type`: `standard_customer`, `high_value_customer`, `small_business`, or `new_customer`.
- `customer_risk_level`: synthetic profile risk category: `Low`, `Medium`, or `High`.
- `is_verified`: synthetic KYC verification flag.

## `accounts`

- `initial_balance`: simulated balance at the beginning of the period.
- `current_balance`: balance after the generated transaction timeline.
- `account_status`: normally `Active`, with a small `Dormant` population.

## `devices` and `device_customer_links`

`devices.customer_id` is retained as a representative/primary owner for the requested schema. The authoritative relationship is `device_customer_links`, which allows one device to be used by multiple customers. This is required to represent the shared-device fraud scenario without flattening a many-to-many relationship.

## `transactions`

- `timestamp`: UTC event timestamp across a period of at least 90 days.
- `amount`: positive transaction amount in the account currency.
- `balance_before`, `balance_after`: simulated account balances around the event.
- `is_fraud`: synthetic ground-truth label used only for evaluation; it is not available to the monitoring rules.
- `fraud_scenario`: scenario label used to evaluate coverage. Normal behavior is labeled `normal`.
- `data_source`: `synthetic_generator`.

## `transaction_features`

The feature table has one row per transaction and includes time, novelty, behavior, geography, velocity and network signals. Important groups include:

- `transaction_hour`, `day_of_week`, `is_night`, `is_weekend`;
- `amount_log`, `amount_percentile`, `amount_vs_customer_average`, `amount_z_score`;
- `is_new_beneficiary`, `is_new_device`, `is_new_country`, `is_high_risk_country`, `is_high_risk_channel`;
- `balance_depletion_ratio`;
- `customer_avg_transaction_amount`, `customer_median_transaction_amount`, `customer_std_transaction_amount`;
- `transactions_last_10_minutes`, `transactions_last_1_hour`, `transactions_last_24_hours`;
- `unique_beneficiaries_last_24_hours`, `unique_devices_last_30_days`;
- `customer_transaction_frequency`, `customer_days_since_registration`;
- `deviation_from_usual_city`, `deviation_from_usual_country`;
- `number_of_customers_per_device`, `number_of_accounts_per_device`;
- `number_of_senders_to_beneficiary`, `number_of_beneficiaries_from_sender`;
- `shared_device_risk`, `beneficiary_network_risk`, `circular_transfer_indicator`, `connected_account_count`;
- `customer_segment`.

The feature engineering module updates its state only after calculating the current row. This is the central leakage-control rule of the project.

## Fraud label policy

The generator includes normal behaviors such as salary credits, utility payments, purchases, subscriptions, travel and business payments. A small minority of rows receive one of the labeled fraud scenarios:

- `night_new_device`
- `unusual_amount_spike`
- `rapid_beneficiary_transfers`
- `new_beneficiary_balance_depletion`
- `shared_device_activity`
- `many_new_beneficiaries`
- `cross_border_activity`
- `circular_account_flow`
- `structuring_pattern`
- `high_risk_customer_behavior`
- `account_takeover_pattern`
- `synthetic_network_cluster`

The final fraud rate is calculated from the generated rows and written to `data/generated/manifest.json`; it is not hardcoded in the dashboard.
