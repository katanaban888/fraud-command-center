"""Relational schema for the fraud monitoring demo.

The schema intentionally keeps analytical facts (transactions, rule results and
features) separate from workflow facts (alerts and investigation cases).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    anonymized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(32), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    registration_date: Mapped[date] = mapped_column(Date, nullable=False)
    occupation: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    customer_risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), nullable=False)
    account_type: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    opening_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    account_status: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (Index("ix_accounts_customer_id", "customer_id"),)


class Device(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.customer_id"))
    device_type: Mapped[str] = mapped_column(String(40), nullable=False)
    operating_system: Mapped[str] = mapped_column(String(40), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(8), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_risk_score: Mapped[float] = mapped_column(Float, nullable=False)


class DeviceCustomerLink(Base):
    __tablename__ = "device_customer_links"

    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (Index("ix_device_links_customer_id", "customer_id"),)


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    beneficiary_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    beneficiary_type: Mapped[str] = mapped_column(String(40), nullable=False)
    country: Mapped[str] = mapped_column(String(8), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    beneficiary_risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sender_account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.account_id"), nullable=False
    )
    sender_customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id"), nullable=False
    )
    beneficiary_id: Mapped[str] = mapped_column(
        ForeignKey("beneficiaries.beneficiary_id"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(60), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    country: Mapped[str] = mapped_column(String(8), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    is_fraud: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fraud_scenario: Mapped[str] = mapped_column(String(80), nullable=False)
    data_source: Mapped[str] = mapped_column(String(60), nullable=False)

    __table_args__ = (
        Index("ix_transactions_timestamp", "timestamp"),
        Index("ix_transactions_customer_timestamp", "sender_customer_id", "timestamp"),
        Index("ix_transactions_beneficiary", "beneficiary_id"),
        Index("ix_transactions_device", "device_id"),
    )


class TransactionFeature(Base):
    __tablename__ = "transaction_features"

    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.transaction_id"), primary_key=True
    )
    transaction_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    is_night: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False)
    amount_log: Mapped[float] = mapped_column(Float, nullable=False)
    amount_percentile: Mapped[float] = mapped_column(Float, nullable=False)
    is_new_beneficiary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_new_device: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_new_country: Mapped[bool] = mapped_column(Boolean, nullable=False)
    balance_depletion_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    customer_avg_transaction_amount: Mapped[float] = mapped_column(Float, nullable=False)
    amount_vs_customer_average: Mapped[float] = mapped_column(Float, nullable=False)
    amount_z_score: Mapped[float] = mapped_column(Float, nullable=False)
    transactions_last_10_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    transactions_last_1_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    transactions_last_24_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_beneficiaries_last_24_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_devices_last_30_days: Mapped[int] = mapped_column(Integer, nullable=False)
    number_of_customers_per_device: Mapped[int] = mapped_column(Integer, nullable=False)
    number_of_senders_to_beneficiary: Mapped[int] = mapped_column(Integer, nullable=False)
    shared_device_risk: Mapped[float] = mapped_column(Float, nullable=False)
    beneficiary_network_risk: Mapped[float] = mapped_column(Float, nullable=False)
    circular_transfer_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False)
    connected_account_count: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_segment: Mapped[str] = mapped_column(String(40), nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.transaction_id"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    alert_status: Mapped[str] = mapped_column(String(32), nullable=False)
    alert_priority: Mapped[str] = mapped_column(String(24), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_rules_json: Mapped[list] = mapped_column(JSON, nullable=False)
    analyst_id: Mapped[str | None] = mapped_column(String(32))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disposition: Mapped[str | None] = mapped_column(String(40))
    investigation_notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_alerts_status", "alert_status"),
        Index("ix_alerts_risk", "risk_score"),
    )


class AlertScoreComponent(Base):
    __tablename__ = "alert_score_components"

    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.alert_id"), primary_key=True)
    component_name: Mapped[str] = mapped_column(String(40), primary_key=True)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    weighted_contribution: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class InvestigationCase(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.alert_id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), nullable=False)
    case_status: Mapped[str] = mapped_column(String(24), nullable=False)
    priority: Mapped[str] = mapped_column(String(24), nullable=False)
    assigned_analyst: Mapped[str | None] = mapped_column(String(32))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_decision: Mapped[str | None] = mapped_column(String(48))
    estimated_loss: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    prevented_loss: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    analyst_comment: Mapped[str | None] = mapped_column(Text)


class RuleResult(Base):
    __tablename__ = "rule_results"

    rule_result_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.transaction_id"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_category: Mapped[str] = mapped_column(String(60), nullable=False)
    triggered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rule_score: Mapped[float] = mapped_column(Float, nullable=False)
    rule_reason: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (Index("ix_rule_results_rule_triggered", "rule_id", "triggered"),)


class RuleDefinition(Base):
    __tablename__ = "rule_definitions"

    rule_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)


class Analyst(Base):
    __tablename__ = "analysts"

    analyst_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    team: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    metric_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40), nullable=False)
    approach: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(40), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    split_name: Mapped[str] = mapped_column(String(40), nullable=False)


class DataQualityResult(Base):
    __tablename__ = "data_quality_results"

    check_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    table_name: Mapped[str] = mapped_column(String(80), nullable=False)
    check_name: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_value: Mapped[float | None] = mapped_column(Float)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BusinessInsight(Base):
    __tablename__ = "business_insights"

    insight_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    metric: Mapped[str] = mapped_column(String(120), nullable=False)
    comparison: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    business_implication: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
