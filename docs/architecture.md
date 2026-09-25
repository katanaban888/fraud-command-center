# Architecture notes

## Phase 1 boundaries

Phase 1 owns synthetic data generation, stable reference entities, database creation and the initial application shells. Feature computation and alert creation intentionally remain separate so that no future rule can accidentally use the synthetic `is_fraud` label as an input.

## Storage abstraction

The generator and future API repositories use SQLAlchemy URLs. SQLite is the local default because it needs no service. PostgreSQL can be selected with `DATABASE_URL` for deployment.

## Shared devices

The requested `devices.customer_id` field is retained as a representative owner. `device_customer_links` is the authoritative relationship table because shared-device signals require one device to be connected to many customers.

## Reproducibility

The pipeline uses `numpy.random.default_rng(seed)`, ordered generation steps and a manifest containing row counts, actual fraud rate, period and scenario counts. Re-running with the same configuration and seed produces the same entity and transaction values apart from the manifest generation timestamp.
