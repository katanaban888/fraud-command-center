# Fraud Command Center

**Explainable transaction monitoring and risk-based alert prioritization**

> Built as an end-to-end portfolio project for Junior Data Analyst, Fraud Analyst and Risk Analyst roles.

## Project summary

Built an end-to-end fraud transaction monitoring platform that combines explainable business rules, behavioral analytics, anomaly detection, risk scoring, alert prioritization and investigation workflow.

This repository is currently in **Phase 1: project setup and reproducible synthetic data**. The dashboard shell, FastAPI service scaffold, relational schema and data generator are now in place. Rule evaluation, risk scoring, alert workflow and model evaluation are added in later phases.

## Business problem

A financial organization cannot manually review every transaction. Fraud and risk teams need a practical monitoring system that can identify unusual activity, prioritize the most important alerts, explain why an event was flagged and support a human investigation process.

This project is designed to demonstrate that workflow with synthetic data. It is not connected to a bank, payment processor or real customer data.

## Current Phase 1 deliverables

- Reproducible generator with a configurable seed.
- 5,000 synthetic customers.
- 6,000 synthetic accounts.
- 3,000 synthetic devices.
- 10,000 synthetic beneficiaries.
- 50,000 synthetic transactions across 120 days.
- Normal behavior and 12 labeled fraud scenarios.
- SQLite database with a PostgreSQL-compatible SQLAlchemy layer.
- FastAPI application with `/api/health`.
- Next.js dark dashboard shell.
- Data dictionary and generated manifest.

## Architecture

```text
Synthetic generator -> SQLite/PostgreSQL -> FastAPI -> Next.js dashboard
          |                    |
          +-> data quality    +-> alerts, cases, rule results and metrics
```

The planned analytical flow is:

```text
transactions
    -> leakage-safe features
    -> explainable rules
    -> composite risk score
    -> prioritized alerts
    -> analyst investigation
    -> model and rule performance metrics
```

## Data model

The main tables are:

- `customers`
- `accounts`
- `devices`
- `device_customer_links`
- `beneficiaries`
- `transactions`
- `transaction_features`
- `rule_results`
- `alerts`
- `alert_score_components`
- `cases`

See [`docs/data_dictionary.md`](docs/data_dictionary.md) for definitions and synthetic-label policy.

## Synthetic data disclaimer

All generated records are synthetic and anonymized. The `is_fraud` column is an artificial evaluation label created by the generator. It does not represent a real investigation outcome or a real bank decision. Actual row counts, fraud rate and scenario distribution are calculated after generation and written to `data/generated/manifest.json`.

## Local installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm 9+

### Backend and pipeline

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Generate the reproducible dataset:

```bash
python -m pipeline.run_pipeline --seed 42
```

This creates:

```text
data/generated/fraud_command_center.db
data/generated/manifest.json
```

The generated files are ignored by Git. The seed and configuration are stored in the repository, so the dataset can be recreated.

Start the API:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the API documentation at <http://localhost:8000/docs> and check <http://localhost:8000/api/health>.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The frontend uses relative `/api` paths and proxies them to `BACKEND_URL`, which avoids browser-side calls to `localhost` in a hosted preview.

## Configuration

Relevant variables are documented in [`.env.example`](.env.example):

- `DATABASE_URL`: SQLite by default; can be replaced with a PostgreSQL SQLAlchemy URL.
- `CORS_ORIGINS`: comma-separated allowed frontend origins.
- `BACKEND_URL`: Next.js rewrite target.

Generation settings are in [`pipeline/config/generation.yml`](pipeline/config/generation.yml).

## Planned analytical methodology

The monitoring layer will combine:

1. rule score;
2. behavioral anomaly score;
3. customer profile score;
4. device score;
5. network score;
6. geographic and channel signal.

The final score will be clipped to 0–100 and grouped as Low, Medium, High or Critical. Every component will be stored separately so analysts can understand the result rather than seeing only one opaque number.

Logistic Regression will be the interpretable baseline model. Isolation Forest will be used as an additional anomaly signal. Neither model will be described as proof of fraud or used to replace human review.

## Roadmap

- **Phase 1:** setup, synthetic data, database schema and data dictionary.
- **Phase 2:** feature engineering, rule engine, risk scoring and data quality.
- **Phase 3:** API, overview dashboard, transaction explorer and alert queue.
- **Phase 4:** alert detail, customer 360, investigations and network analysis.
- **Phase 5:** ML evaluation, rule tuning and business insights.
- **Phase 6:** tests, SQL library, notebooks, deployment documentation and screenshots.

## Ethical considerations

- The project uses synthetic data only.
- A risk score is a prioritization signal, not proof of fraud.
- Automated decisions should receive human review.
- Models can contain bias, especially around geography, age, customer segment and device behavior.
- Sensitive demographic or geographic fields must not be used for adverse action without fairness analysis.
- No real card numbers, identity documents, bank accounts or personal data are included.

## License and portfolio use

This is a demonstration project for educational and portfolio purposes. It should not be used to block real customers or make real financial decisions.
