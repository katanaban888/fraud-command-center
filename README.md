# Fraud Command Center

**Explainable transaction monitoring and risk-based alert prioritization**

> An end-to-end portfolio project for Junior Data Analyst, Fraud Analyst and Risk Analyst roles.

## Project summary

Built an end-to-end fraud transaction monitoring platform that combines explainable business rules, behavioral analytics, anomaly detection, risk scoring, alert prioritization and investigation workflow.

The product is intentionally presented as a realistic risk-operations workspace rather than a notebook with disconnected charts. It contains a reproducible synthetic data pipeline, a relational data model, chronological feature engineering, configurable rules, risk-score contributions, ML evaluation, an alert queue, customer 360, network context, case management and data-quality monitoring.

## Important disclaimer

This is a portfolio demonstration using **synthetic data only**. It is not connected to a bank, payment processor or real customer data. Synthetic labels are used for evaluation and do not represent real fraud decisions. A risk score is a prioritization signal, not proof of fraud. Production decisions require human review, controls, calibration, monitoring and fairness analysis.

## Business problem

Financial organizations process more transactions than analysts can manually inspect. A fraud/risk team needs to:

- identify unusual behavior;
- rank alerts by risk and potential impact;
- explain which rules and features contributed;
- understand related customers, devices and beneficiaries;
- measure false positives and analyst workload;
- tune thresholds without optimizing only for fewer alerts;
- record investigation notes and decisions.

Fraud Command Center demonstrates this workflow with generated activity covering more than 90 days.

## Current generated dataset

Running the default pipeline with `seed=42` currently creates:

| Entity | Rows |
|---|---:|
| Customers | 5,000 |
| Accounts | 6,000 |
| Devices | 3,000 |
| Customer-device links | 8,855 |
| Beneficiaries | 10,000 |
| Transactions | 50,000 |
| Transaction period | 120 days |
| Synthetic fraud rate | 2.00% |
| Prioritized alerts | 2,939 |
| Seeded open cases | 24 |

The exact result is calculated and written to `data/generated/manifest.json`; these values are not manually inserted into the dashboard. Generated artifacts are ignored by Git and can be recreated with the seed.

## Main features

### Analytics and pipeline

- deterministic synthetic data generator;
- normal behavior: salary credits, utilities, purchases, subscriptions, travel and small-business payments;
- 12 labeled fraud scenarios;
- chronological, leakage-safe features;
- R001–R012 explainable rules;
- V1 and V2 threshold comparison;
- 0–100 composite risk score with saved component contributions;
- Logistic Regression baseline;
- Isolation Forest anomaly signal;
- time-based model evaluation;
- precision, recall, F1, ROC-AUC and PR-AUC;
- false-positive and workload estimates;
- data-quality score with explicit penalty composition;
- automatically generated business insights.

### Analyst workspace

- Overview dashboard with filters and KPI cards;
- Alert Queue with search, pagination, sorting, workflow status changes and CSV export;
- Alert Detail with “Why was this flagged?”, rule evidence, score breakdown and timeline;
- Transaction Explorer and transaction detail;
- Customer Risk / customer 360;
- Network Analysis for customers, accounts, devices and beneficiaries;
- Rule Performance and V1/V2 comparison;
- Rule Tuning threshold simulation;
- Model Evaluation;
- Investigations case management;
- Data Quality monitoring;
- Business Insights;
- English UI with a future localization structure.

## Architecture

```text
Synthetic Data Generator
          |
          v
Raw entities and chronological transactions
          |
          +--> Data Quality Checks
          |
          v
Leakage-safe Feature Engineering
          |
          v
V1 / V2 Explainable Rule Engine
          |
          +--> Rule Results
          |
          v
ML signals: Logistic Regression + Isolation Forest
          |
          v
Composite Risk Score and Alert Queue
          |
          v
SQLite / PostgreSQL
          |
          v
FastAPI REST API
          |
          v
Next.js Dashboard
```

The browser uses relative `/api` URLs. The Next.js development server proxies those requests to `BACKEND_URL`, so browser-facing code does not depend on `localhost` when the application is hosted behind a preview or deployment proxy.

## Data model

Core tables:

- `customers`: anonymized profiles and profile-risk levels;
- `accounts`: customer-owned accounts and simulated balances;
- `devices`: canonical devices and device metadata;
- `device_customer_links`: many-to-many customer/device relationship;
- `beneficiaries`: destination profiles;
- `transactions`: chronological financial facts and synthetic ground truth;
- `transaction_features`: pre-event behavioral and network features;
- `rule_results`: triggered rule evidence;
- `alerts`: analyst queue records;
- `alert_score_components`: explainable score contributions;
- `cases`: investigation workflow;
- `model_metrics`: model comparison metrics;
- `data_quality_results`: validation results;
- `business_insights`: calculated findings.

The required `devices.customer_id` field is retained as a representative owner. `device_customer_links` is authoritative for shared-device analysis because one device can be used by many customers.

See [`docs/data_dictionary.md`](docs/data_dictionary.md).

## Fraud scenarios

The generator includes:

1. night transaction with a new device;
2. unusual amount spike;
3. rapid transfers to a beneficiary;
4. new beneficiary followed by balance depletion;
5. shared device activity;
6. many new beneficiaries;
7. cross-border activity;
8. circular account-flow candidate;
9. structuring pattern;
10. high-risk customer behavior;
11. account takeover pattern;
12. synthetic network cluster.

Fraud labels remain rare and the exact class distribution is calculated after generation.

## Feature engineering and leakage policy

Features are calculated chronologically. Current-row `is_fraud` and `fraud_scenario` are not read by the feature module.

Examples:

- transaction hour, weekend and night flags;
- log amount, customer percentile, amount-to-average and z-score;
- new device, beneficiary and country;
- balance depletion ratio;
- 10-minute, one-hour and 24-hour velocity;
- unique beneficiaries and devices in lookback windows;
- customer frequency and registration tenure;
- geographic deviation;
- customers/accounts per device;
- senders per beneficiary;
- shared-device and beneficiary network risk;
- connected-account and circular-flow indicators;
- customer segments.

## Rule engine

Rules are configured in [`pipeline/config/rules.yml`](pipeline/config/rules.yml). Each triggered rule stores:

- rule ID and version;
- rule name and category;
- score contribution;
- severity;
- reason text;
- evidence values.

The current engine includes R001–R012 from the project specification. Version 1 uses broader thresholds. Version 2 adds stronger behavioral and network context. Rule metrics are calculated against the synthetic label and are presented as analytical evaluation, not business truth.

## Risk scoring methodology

The score is clipped to 0–100:

```text
risk_score = clip(
    0.45 * rule_score
  + 0.20 * behavioral_score
  + 0.10 * customer_score
  + 0.10 * device_score
  + 0.10 * network_score
  + 0.05 * geo_channel_score,
  0,
  100
)
```

Risk levels:

```text
0–29   Low
30–59  Medium
60–79  High
80–100 Critical
```

Weights are stored in [`pipeline/config/risk_scoring.yml`](pipeline/config/risk_scoring.yml). The alert queue uses a prioritized score threshold of 50 by default to reduce manual workload relative to reviewing every low/medium event. Threshold simulation is available in the UI.

Estimated prevented loss is a counterfactual portfolio metric using a documented prevention-rate assumption. It is not measured savings.

## ML approach

### Logistic Regression

- interpretable baseline;
- standardized numerical features;
- class-balanced training;
- chronological train/test split;
- coefficient importance displayed in the UI.

### Isolation Forest

- unsupervised anomaly signal;
- fitted only as a supporting signal;
- normalized to 0–100;
- does not independently determine fraud.

Compared approaches:

- rules-only;
- rules + Isolation Forest;
- rules + Logistic Regression;
- rules + combined score.

Because the positive class is rare, precision, recall, F1, PR-AUC and workload are emphasized over accuracy. No approach automatically blocks a customer.

## Example calculated run

For the current default seed, the pipeline calculates 50,000 transactions, 1,000 synthetic fraud labels and 2,939 prioritized alerts. The current queue contains 480 synthetic fraud-labelled transactions, giving a 16.33% synthetic queue precision proxy. The combined model comparison reports its own threshold-based precision, recall and PR-AUC in `data/generated/model_metrics.json` and the Model Evaluation page.

These values are outputs of the current generated dataset, not hardcoded success claims.

## Dashboard screenshots / demo

The repository includes a demo-ready live dashboard shell and all requested route pages. For screenshots, open `/overview`, `/alerts`, `/alerts/{alert_id}`, `/customers/{customer_id}`, `/rules`, `/rules/tuning` and `/models` after generating the database.

## Local installation

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm 9+

### Backend and data pipeline

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
cp .env.example .env
python -m pipeline.run_pipeline --seed 42
```

The full command creates the raw dataset, features, rules, scores, alerts, model artifacts, quality results, insights and database:

```text
data/generated/fraud_command_center.db
data/generated/manifest.json
data/generated/model_metrics.json
data/generated/rule_performance.json
data/generated/data_quality.json
data/generated/insights.json
```

Generated data is intentionally ignored by Git. Re-run the same command to reproduce it.

Start the API:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

- API health: <http://localhost:8000/api/health>
- Swagger: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

For a production build:

```bash
npm run lint
npm run build
npm start
```

## Environment variables

See [`.env.example`](.env.example):

- `DATABASE_URL`: `sqlite:///./data/generated/fraud_command_center.db` locally, or a PostgreSQL SQLAlchemy URL in deployment;
- `CORS_ORIGINS`: comma-separated frontend origins;
- `BACKEND_URL`: FastAPI URL used by the Next.js rewrite;
- `APP_ENV`: environment label.

## API documentation

Implemented endpoints:

```text
GET    /api/health
GET    /api/overview
GET    /api/transactions
GET    /api/transactions/{transaction_id}
GET    /api/customers
GET    /api/customers/{customer_id}
GET    /api/alerts
GET    /api/alerts/{alert_id}
PATCH  /api/alerts/{alert_id}
GET    /api/cases
GET    /api/cases/analytics
POST   /api/cases
PATCH  /api/cases/{case_id}
GET    /api/rules
GET    /api/rules/performance
POST   /api/rules/simulate
GET    /api/network/related/{entity_id}
GET    /api/model/metrics
GET    /api/data-quality
GET    /api/insights
GET    /api/export/alerts
```

All list endpoints support pagination where applicable. Transaction and alert endpoints support filtering, searching and sorting. Input payloads are validated with Pydantic.

## SQL and notebooks

The [`sql/`](sql/) directory contains 15 business-question SQL files using joins, CTEs, windows, aggregations and `CASE WHEN` logic. SQLite date functions are used for the local default; PostgreSQL equivalents can be swapped for deployment.

The [`notebooks/`](notebooks/) directory contains:

- `01_eda.ipynb`;
- `02_feature_engineering.ipynb`;
- `03_rule_engine.ipynb`;
- `04_model_evaluation.ipynb`;
- `05_business_analysis.ipynb`.

They are intended for reproducible exploration; production calculations live in `pipeline/` and the API.

## Testing

```bash
.venv/bin/pytest
.venv/bin/ruff check backend pipeline tests scripts
cd frontend && npm run lint && npm run build
```

The tests cover:

- reproducible generation;
- required row counts and identifiers;
- non-negative balances and amounts;
- chronological, label-free features;
- rule versions and explanations;
- risk score bounds and score contributions;
- API health, filtering, pagination and unknown IDs.

## Deployment direction

### Frontend — Vercel

- set the project root to `frontend`;
- set `BACKEND_URL` to the deployed FastAPI URL;
- build command: `npm run build`;
- start command is managed by Vercel.

### Backend — Render / Railway

- build: `pip install -e .`;
- start: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`;
- use PostgreSQL by setting `DATABASE_URL`;
- run the pipeline as a release/job step before serving the dashboard.

## Project structure

```text
backend/       FastAPI app, schema, repositories and API routes
frontend/      Next.js dashboard routes and reusable UI
pipeline/      generator, features, rules, scoring, ML and analytics
sql/           business-question SQL library
notebooks/     reproducible exploratory notebooks
tests/         Python tests
docs/          architecture, API notes and data dictionary
```

## Business recommendations from the analytical workflow

The application calculates recommendations from the current seed rather than storing a fixed narrative. Typical actions supported by the metrics are:

- tune high-volume, low-precision rules;
- segment thresholds by customer behavior;
- combine shared-device signals with velocity or amount deviation;
- review beneficiary concentration alongside transaction context;
- monitor analyst minutes and SLA age, not just alert volume;
- use PR-AUC and recall/precision trade-offs for model threshold selection;
- require investigator review before adverse customer action.

## Limitations and future improvements

- synthetic behavior is not a substitute for production labels;
- no authentication or role-based access control yet;
- no real-time event streaming;
- SQLite is for local demonstration; PostgreSQL is the deployment path;
- prevented-loss estimates are assumptions;
- model calibration, drift monitoring and fairness analysis would be required in production;
- optional graph visualization and SHAP explanations can be added later;
- production systems need immutable audit logs and stronger data-governance controls.

## Ethical considerations

- customer data in this repository is anonymized and synthetic;
- the risk score does not prove fraud;
- automatic blocking should not be implemented from this demo alone;
- age, gender, geography and other sensitive attributes require fairness review;
- real financial data must not be committed to a public portfolio repository;
- human review, appeal paths and investigator accountability are required for customer-impacting decisions.
